import os
import uuid
from pathlib import Path
from functools import lru_cache
from typing import List, Optional, Tuple
from django.conf import settings
from django.utils.text import slugify
from django.core.files.storage import FileSystemStorage
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

import spacy
from rapidfuzz import process, fuzz

try:
    nlp = spacy.load("en_core_web_sm")
except Exception: 
    nlp = None

MEDIA_ROOT = Path(settings.MEDIA_ROOT)
MEDIA_URL = settings.MEDIA_URL.rstrip('/') + '/'

FUZZY_SCORE_THRESHOLD = 70
MAX_RETURN_IMAGES = 200
DIRECTION_WORDS = {"north", "south", "east", "west", "n", "s", "e", "w"}

ALIASES = {
    "bombay": "Mumbai",
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "madras": "Chennai",
    "chennai": "Chennai",
    "delhi": "New Delhi",
    "newdelhi": "New Delhi",
}

def humanize_folder_name(folder: str) -> str:
    """Convert slug-like folder to human-ish name: new-delhi -> New Delhi"""
    return folder.replace('-', ' ').title()

@lru_cache(maxsize=1)
def discover_known_locations() -> List[str]:
    """
    Returns a list of human-readable known locations discovered from MEDIA_ROOT top-level folders.
    Caching avoids repeated disk reads.
    """
    if not MEDIA_ROOT.exists():
        return []
    locs = []
    for p in MEDIA_ROOT.iterdir():
        if p.is_dir():
            locs.append(humanize_folder_name(p.name))
    # include aliases in known set as low-priority choices
    # (we won't duplicate names that already exist)
    for k, v in ALIASES.items():
        if v not in locs:
            locs.append(v)
    return sorted(locs)

def spaCy_extract_locations(text: str) -> List[str]:
    """Return candidate location strings using spaCy NER (GPE/LOC/FAC/ORG)."""
    if not nlp:
        return []
    doc = nlp(text)
    candidates = []
    for ent in doc.ents:
        if ent.label_ in ("GPE", "LOC", "FAC", "ORG"):
            candidates.append(ent.text.strip())
    return candidates

def ngram_candidates_from_text(text: str, n_max: int = 3) -> List[str]:
    """Return n-grams (1..n_max tokens) from text for fallback matching."""
    tokens = [t.strip('.,()[]{};:') for t in text.split() if t.strip()]
    tokens = [t for t in tokens if len(t) > 1]  # drop single weird chars
    ngrams = []
    for n in range(1, min(n_max, len(tokens)) + 1):
        for i in range(len(tokens) - n + 1):
            ngrams.append(" ".join(tokens[i:i+n]))
    # return longer ngrams first
    return sorted(set(ngrams), key=lambda s: -len(s))

def best_fuzzy_match(candidate: str, choices: List[str]) -> Optional[Tuple[str, float]]:
    """Return (best_choice, score) or None."""
    if not choices:
        return None
    match = process.extractOne(candidate, choices, scorer=fuzz.token_sort_ratio)
    # match is (choice, score, idx)
    if match and match[1] >= FUZZY_SCORE_THRESHOLD:
        return (match[0], float(match[1]))
    return None

def find_best_location_from_text(text: str) -> Optional[Tuple[str, float, Optional[str]]]:
    """
    Attempt to find best matching location and optional sublocation hint.
    Returns (matched_location, score, sublocation_or_None) or None.
    Strategy:
      1) spaCy NER candidates -> fuzzy match against known locations
      2) ngram candidates (1..3) -> fuzzy match
      3) fallback: fuzzy match whole text
    Sublocation (direction) is only used if there is an explicit directional token in text.
    """
    known = discover_known_locations()
    if not known:
        return None

    direction_hint = None
    # detect direction tokens (simple)
    for tok in text.lower().split():
        tok_clean = tok.strip('.,?!()[]{}')
        if tok_clean in DIRECTION_WORDS:
            mapping = {"n":"North","s":"South","e":"East","w":"West"}
            direction_hint = mapping.get(tok_clean, tok_clean.title())
            break

    # 1) spaCy
    candidates = spaCy_extract_locations(text)
    for cand in candidates:
        # quick alias resolution (e.g., 'bombay' -> 'Mumbai')
        cand_lower = cand.lower().replace(" ", "")
        if cand_lower in ALIASES:
            cand = ALIASES[cand_lower]
        res = best_fuzzy_match(cand, known)
        if res:
            return (res[0], res[1], direction_hint)

    # 2) n-grams fallback
    for ngr in ngram_candidates_from_text(text, n_max=3):
        res = best_fuzzy_match(ngr, known)
        if res:
            return (res[0], res[1], direction_hint)

    # 3) whole-text fuzzy
    res = best_fuzzy_match(text, known)
    if res:
        return (res[0], res[1], direction_hint)

    return None

def gather_urls_for_location(location: str, use_sublocation: Optional[str] = None, limit: int = MAX_RETURN_IMAGES) -> List[str]:
    """
    Collect public URLs for files under MEDIA_ROOT/<slug(location)>[/<slug(sublocation)>]/...
    Returns up to `limit` URLs. Uses request.build_absolute_uri at view time.
    """
    slug_loc = slugify(location)
    base = MEDIA_ROOT / slug_loc
    if use_sublocation:
        base = base / slugify(use_sublocation)
    if not base.exists():
        return []

    urls = []
    for root, _, files in os.walk(base):
        for fname in files:
            # build media-relative path
            rel = os.path.relpath(os.path.join(root, fname), start=MEDIA_ROOT).replace("\\", "/")
            urls.append(MEDIA_URL + rel)
            if len(urls) >= limit:
                break
        if len(urls) >= limit:
            break
    return urls


def _build_path(location: str, sublocation: str, filename: str) -> str:
    """Return relative path under MEDIA_ROOT: location/sublocation/slugifiedfilename-<uid>.<ext>"""
    name, ext = os.path.splitext(filename)
    safe_name = slugify(name)[:50] or 'image'
    uid = uuid.uuid4().hex[:8]
    loc = slugify(location or 'unknown')
    sub = slugify(sublocation) if sublocation else 'general'
    rel_path = os.path.join(loc, sub, f"{safe_name}-{uid}{ext}")
    return rel_path

@api_view(['POST'])
@permission_classes([AllowAny])
def raw_upload(request):
    """
    POST /api/upload_raw/
    Expects multipart/form-data with fields: location, sublocation (opt), file (single file).
    Saves file to MEDIA_ROOT/<location>/<sublocation>/...
    Returns JSON: { 'rel_path', 'url' }
    """
    uploaded = request.FILES.get('file') or request.FILES.get('image')
    if not uploaded:
        return Response({'detail': 'No file provided (expected form field "file" or "image").'},
                        status=status.HTTP_400_BAD_REQUEST)

    location = request.POST.get('location') or request.data.get('location') or 'unknown'
    sublocation = request.POST.get('sublocation') or request.data.get('sublocation') or ''

    rel_path = _build_path(location, sublocation, uploaded.name)
    abs_dir = MEDIA_ROOT / Path(rel_path).parent
    abs_dir.mkdir(parents=True, exist_ok=True)

    fs = FileSystemStorage(location=str(MEDIA_ROOT))
    saved_name = fs.save(rel_path, uploaded)
    url = request.build_absolute_uri(settings.MEDIA_URL + saved_name.replace('\\','/'))

    return Response({
        'rel_path': saved_name.replace('\\','/'),
        'url': url
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def extract_location_and_fetch_images(request):
    """
    POST /api/extract_and_fetch/
    JSON body:
      {
        "text": "Please give me x & y data about Pune",
        "max_images": 50   # optional
      }

    Response (200):
    {
      "query": "...",
      "matched_location": "Pune",
      "confidence": 86.5,
      "sublocation_used": null,
      "image_count": 3,
      "images": [
         "http://127.0.0.1:8000/media/pune/img1.jpg",
         ...
      ]
    }

    404 if no match found.
    """
    data = request.data or {}
    text = (data.get('text') or '').strip()
    if not text:
        return Response({"detail": "Provide 'text' in JSON body."}, status=status.HTTP_400_BAD_REQUEST)

    max_images = int(data.get('max_images') or MAX_RETURN_IMAGES)

    found = find_best_location_from_text(text)
    if not found:
        return Response({"detail": "No known location matched from the input."}, status=status.HTTP_404_NOT_FOUND)

    matched_location, score, sub_hint = found

    # Prefer to NOT use sublocation unless user explicitly requested one:
    # check for explicit directional token in text or exact sublocation name match.
    explicit_sublocation = None
    # small heuristic: if the text contains the exact word "north|south|east|west" use it
    for w in text.lower().split():
        w2 = w.strip('.,?!()[]{}')
        if w2 in DIRECTION_WORDS:
            mapping = {"n":"North","s":"South","e":"East","w":"West"}
            explicit_sublocation = mapping.get(w2, w2.title())
            break

    use_subloc = explicit_sublocation or None  # only if explicit

    # gather urls (these are media-relative; convert to absolute URIs now)
    raw_urls = gather_urls_for_location(matched_location, use_subloc, limit=max_images)
    abs_urls = [request.build_absolute_uri(u) for u in raw_urls]

    return Response({
        "query": text,
        "matched_location": matched_location,
        "confidence": round(score, 2),
        "sublocation_used": use_subloc,
        "image_count": len(abs_urls),
        "images": abs_urls
    }, status=status.HTTP_200_OK)