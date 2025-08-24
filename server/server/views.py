import os
import uuid
from pathlib import Path
from django.conf import settings
from django.utils.text import slugify
from django.core.files.storage import FileSystemStorage
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

MEDIA_ROOT = Path(settings.MEDIA_ROOT)

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
