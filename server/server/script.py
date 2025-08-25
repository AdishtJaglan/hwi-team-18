import json
import re
import os
import requests
import geopandas as gpd
import google.generativeai as genai
from datetime import datetime
from typing import Optional, Dict, Any, List
from shapely.geometry import box as shapely_box
from shapely.geometry import shape, LineString, Point, Polygon

__all__ = ["SimpleQueryProcessor", "process_query_once"]

class SimpleQueryProcessor:
    def __init__(self, gemini_api_key: Optional[str] = None, verbose: bool = False):
        """
        Initialize the processor.
        gemini_api_key: API key string or None. If None, environment variable GEMINI_API_KEY is used.
        verbose: when True, prints status messages.
        """
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.verbose = verbose
        self.gemini_model = self._setup_gemini()
        self.query_counter = 0

    def _log(self, *args, **kwargs):
        if self.verbose:
            print(*args, **kwargs)

    def _setup_gemini(self):
        """Attempt to initialize Gemini models; return the first working model or None."""
        if not self.gemini_api_key:
            self._log("⚠️ No Gemini API key provided.")
            return None

        try:
            genai.configure(api_key=self.gemini_api_key)
            models_to_try = ['gemini-2.0-flash-lite']

            for model_name in models_to_try:
                try:
                    self._log(f"   Trying Gemini model: {model_name}...")
                    gemini_model = genai.GenerativeModel(model_name)
                    # quick smoke test
                    gemini_model.generate_content("Hello")
                    self._log(f"✅ Gemini AI initialized successfully with {model_name}")
                    return gemini_model
                except Exception:
                    continue

            self._log("❌ All Gemini models failed to initialize")
            return None

        except Exception as e:
            self._log(f"❌ Failed to initialize Gemini AI: {e}")
            return None

    def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process a single query and return the result dictionary."""
        self.query_counter += 1
        self._log(f"🔍 Processing Query: {user_query[:50]}...")

        location = self.extract_location(user_query)
        classification = self.classify_query(user_query)

        response = {
            "query_id": f"Q{self.query_counter:04d}",
            "timestamp": datetime.now().isoformat(),
            "user_query": user_query,
            "location": {
                "name": location.get("location_name", "Unknown"),
                "type": location.get("location_type", "general"),
                "coordinates": location.get("coordinates", {}),
                "bbox": location.get("bbox", []),
                "confidence": location.get("confidence", 0.0)
            },
            "classification": {
                "category": classification.get("query_category", "general"),
                "intent": classification.get("query_intent", "information"),
                "priority": classification.get("priority_level", "medium"),
                "confidence": classification.get("confidence", 0.0)
            },
            "analysis": {
                "type": classification.get("analysis_type", "statistical"),
                "metrics": classification.get("specific_metrics", []),
                "requires_comparison": classification.get("requires_comparison", False),
                "estimated_time": "minutes"
            },
            "recommendations": self.get_recommendations(classification.get("query_category", "general"))
        }

        bbox = response.get("location", {}).get("bbox", [])
        if bbox and len(bbox) == 4 and all(v is not None for v in bbox):
            aoi_result = self.run_aoi_osm_queries(bbox)
            response["analysis"]["osm_status"] = aoi_result.get("osm_status")
            response["analysis"]["osm_summary"] = aoi_result.get("osm_summary")
            gemini_res = self.generate_gemini_insights(response)
            response["analysis"]["gemini_status"] = gemini_res.get("gemini_status")
            response["analysis"]["gemini_insights"] = gemini_res.get("gemini_insights")
        else:
            response["analysis"]["osm_status"] = "no_bbox"
            response["analysis"]["osm_summary"] = None
        
        return response

    def extract_location(self, query: str) -> Dict[str, Any]:
        """Extract location information from query using Gemini if available; fallback otherwise."""
        if not self.gemini_model:
            return self._fallback_location_extraction(query)

        try:
            location_prompt = f"""
            Extract location from this query and return ONLY a JSON object:

            QUERY: "{query}"

            Return this exact JSON structure:
            {{
                "location_type": "city|coordinates|area|general",
                "location_name": "extracted name or 'General Area'",
                "coordinates": {{"lat": number or null, "lon": number or null}},
                "bbox": [min_lon, min_lat, max_lon, max_lat],
                "confidence": 0.0-1.0
            }}

            Rules:
            - If city mentioned: use "city", extract name, set coordinates
            - If coordinates mentioned: use "coordinates", parse lat/lon
            - If no location: use "general", "General Area", null coordinates
            - For cities: generate bbox ±0.1 degrees around coordinates
            - Set confidence: 0.9 for cities, 0.8 for coordinates, 0.3 for general

            Return ONLY the JSON, no other text.
            """

            response = self.gemini_model.generate_content(location_prompt)
            response_text = getattr(response, "text", str(response)).strip()

            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start != -1 and json_end != 0:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
            else:
                return self._fallback_location_extraction(query)

        except Exception as e:
            self._log(f"⚠️ Gemini location extraction failed: {e}")
            return self._fallback_location_extraction(query)

    def _fallback_location_extraction(self, query: str) -> Dict[str, Any]:
        """Fallback location extraction without Gemini."""
        query_lower = query.lower()

        cities = {
            "delhi": {"lat": 28.6139, "lon": 77.2090},
            "mumbai": {"lat": 19.0760, "lon": 72.8777},
            "bangalore": {"lat": 12.9716, "lon": 77.5946},
            "chennai": {"lat": 13.0827, "lon": 80.2707},
            "kolkata": {"lat": 22.5726, "lon": 88.3639},
            "hyderabad": {"lat": 17.3850, "lon": 78.4867},
            "pune": {"lat": 18.5204, "lon": 73.8567},
            "ahmedabad": {"lat": 23.0225, "lon": 72.5714},
            "jaipur": {"lat": 26.9124, "lon": 75.7873},
            "lucknow": {"lat": 26.8467, "lon": 80.9462}
        }

        coord_match = re.search(r'(\d+\.?\d*)[,\s]+(\d+\.?\d*)', query)
        if coord_match:
            try:
                lat = float(coord_match.group(1))
                lon = float(coord_match.group(2))
                return {
                    "location_type": "coordinates",
                    "location_name": f"Coordinates {lat}, {lon}",
                    "coordinates": {"lat": lat, "lon": lon},
                    "bbox": [lon - 0.05, lat - 0.05, lon + 0.05, lat + 0.05],
                    "confidence": 0.8
                }
            except ValueError:
                pass

        for city, coords in cities.items():
            if city in query_lower:
                return {
                    "location_type": "city",
                    "location_name": city.title(),
                    "coordinates": coords,
                    "bbox": [coords["lon"] - 0.1, coords["lat"] - 0.1, coords["lon"] + 0.1, coords["lat"] + 0.1],
                    "confidence": 0.9
                }

        return {
            "location_type": "general",
            "location_name": "General Area",
            "coordinates": {"lat": None, "lon": None},
            "bbox": [77.0, 28.0, 77.5, 28.5],
            "confidence": 0.3
        }

    def classify_query(self, query: str) -> Dict[str, Any]:
        """Classify query using Gemini if available; fallback otherwise."""
        if not self.gemini_model:
            return self._fallback_classification(query)

        try:
            classification_prompt = f"""
            Classify this satellite infrastructure query and return ONLY a JSON object:

            QUERY: "{query}"

            Return this exact JSON structure:
            {{
                "query_category": "infrastructure|quality_of_life|road_conditions|industry|comparison|general",
                "query_intent": "analysis|comparison|prediction|assessment|information",
                "analysis_type": "spatial|statistical|comparative|predictive",
                "priority_level": "high|medium|low",
                "specific_metrics": ["roads", "buildings", "hospitals", "schools", "intersections"],
                "requires_comparison": true|false,
                "confidence": 0.0-1.0
            }}

            Return ONLY the JSON, no other text.
            """

            response = self.gemini_model.generate_content(classification_prompt)
            response_text = getattr(response, "text", str(response)).strip()

            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start != -1 and json_end != 0:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
            else:
                return self._fallback_classification(query)

        except Exception as e:
            self._log(f"⚠️ Gemini classification failed: {e}")
            return self._fallback_classification(query)

    def _fallback_classification(self, query: str) -> Dict[str, Any]:
        """Fallback classification logic."""
        query_lower = query.lower()

        if any(word in query_lower for word in ['road', 'building', 'intersection', 'infrastructure', 'development']):
            category = "infrastructure"
        elif any(word in query_lower for word in ['healthcare', 'hospital', 'school', 'education', 'quality', 'life', 'amenity']):
            category = "quality_of_life"
        elif any(word in query_lower for word in ['traffic', 'transportation', 'connectivity', 'road condition']):
            category = "road_conditions"
        elif any(word in query_lower for word in ['commercial', 'residential', 'business', 'industrial', 'store']):
            category = "industry"
        elif any(word in query_lower for word in ['compare', 'versus', 'vs', 'difference', 'between']):
            category = "comparison"
        else:
            category = "general"

        if any(word in query_lower for word in ['compare', 'versus', 'vs', 'difference']):
            intent = "comparison"
        elif any(word in query_lower for word in ['predict', 'future', 'will', 'going to']):
            intent = "prediction"
        elif any(word in query_lower for word in ['analyze', 'analysis', 'detailed']):
            intent = "analysis"
        elif any(word in query_lower for word in ['assess', 'status', 'current', 'how']):
            intent = "assessment"
        else:
            intent = "information"

        metrics: List[str] = []
        if any(word in query_lower for word in ['road', 'highway', 'street']):
            metrics.append("roads")
        if any(word in query_lower for word in ['building', 'structure']):
            metrics.append("buildings")
        if any(word in query_lower for word in ['hospital', 'medical', 'clinic']):
            metrics.append("hospitals")
        if any(word in query_lower for word in ['school', 'education', 'university']):
            metrics.append("schools")
        if any(word in query_lower for word in ['intersection', 'crossing', 'junction']):
            metrics.append("intersections")

        return {
            "query_category": category,
            "query_intent": intent,
            "analysis_type": "spatial" if "area" in query_lower or "location" in query_lower else "statistical",
            "priority_level": "high" if any(word in query_lower for word in ['urgent', 'important', 'critical']) else "medium",
            "specific_metrics": metrics,
            "requires_comparison": intent == "comparison",
            "confidence": 0.8 if category != "general" else 0.6
        }

    def get_recommendations(self, category: str) -> List[str]:
        """Return recommendations for a category."""
        recommendations = {
            "infrastructure": [
                "Analyze road network density",
                "Assess building infrastructure",
                "Evaluate intersection quality"
            ],
            "quality_of_life": [
                "Check healthcare accessibility",
                "Evaluate educational facilities",
                "Assess amenity coverage"
            ],
            "road_conditions": [
                "Analyze traffic patterns",
                "Assess road connectivity",
                "Evaluate transportation infrastructure"
            ],
            "industry": [
                "Analyze commercial development",
                "Assess residential infrastructure",
                "Evaluate industrial potential"
            ],
            "comparison": [
                "Generate comparative reports",
                "Create visualization charts",
                "Provide ranking analysis"
            ],
            "general": [
                "Conduct comprehensive analysis",
                "Generate overview report",
                "Create development roadmap"
            ]
        }

        return recommendations.get(category, ["Analyze the area", "Generate report", "Provide insights"])

    def save_response(self, response: Dict[str, Any], output_dir: str = "query_responses") -> str:
        """Save response to a JSON file and return path."""
        os.makedirs(output_dir, exist_ok=True)
        filename = f"query_response_{response['query_id']}.json"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(response, f, indent=2, ensure_ascii=False)
        self._log(f"💾 Response saved to: {filepath}")
        return filepath

    def run_aoi_osm_queries(self, bbox: list) -> dict:
        """
        Run Overpass / OSM analysis for bbox = [min_lon, min_lat, max_lon, max_lat].
        Uses user-provided helper functions (bbox_polygon, overpass, osm_to_gdf,
        length_km, intersection_density_per_km2, point_density_per_km2, norm_clip).
        Returns dict: {"osm_summary": {...}, "osm_status": "ok" | "error: ..."}
        """
        # validate bbox
        if not bbox or len(bbox) != 4 or any(v is None for v in bbox):
            return {"osm_summary": None, "osm_status": "invalid_bbox"}

        try:
            # ---- area (km2) ----
            # bbox provided as [min_lon, min_lat, max_lon, max_lat]
            min_lon, min_lat, max_lon, max_lat = bbox
            poly = bbox_polygon([min_lon, min_lat, max_lon, max_lat])  # user impl
            aoi = gpd.GeoDataFrame([{"geometry": poly}], crs="EPSG:4326")
            area_km2 = aoi.to_crs(3857).area.iloc[0] / 1e6

            # ---------- OSM QUERIES ----------
            # Overpass bbox expects (minlat,minlon,maxlat,maxlon)
            Q_BASE = f"({min_lat},{min_lon},{max_lat},{max_lon})"

            Q_ROADS = f"""
            [out:json][timeout:60];
            way{Q_BASE}[highway];
            out geom;
            """
            Q_BUILD = f"""
            [out:json][timeout:60];
            way{Q_BASE}[building];
            out geom;
            """
            Q_AMEN = f"""
            [out:json][timeout:60];
            (
              node{Q_BASE}[amenity=hospital];
              node{Q_BASE}[amenity=clinic];
              node{Q_BASE}[amenity=school];
              node{Q_BASE}[amenity=university];
              node{Q_BASE}[public_transport=station];
              node{Q_BASE}[highway=bus_stop];
            );
            out body;
            """

            # run queries (user implementations)
            roads = osm_to_gdf(overpass(Q_ROADS))
            build = osm_to_gdf(overpass(Q_BUILD))
            amen  = osm_to_gdf(overpass(Q_AMEN), geom_types=("node",))

            # ---------- CLIP TO BBOX (robust, exactly as you provided) ----------
            roads = gpd.overlay(roads, aoi, how="intersection") if not roads.empty else roads
            build = gpd.overlay(build, aoi, how="intersection") if not build.empty else build
            amen  = gpd.overlay(amen,  aoi, how="intersection") if not amen.empty  else amen

            # ---------- METRICS (exact code you supplied) ----------
            road_km = length_km(roads)
            road_km_per_km2 = 0.0 if area_km2 == 0 else road_km / area_km2
            bldg_count = 0 if build.empty else len(build)
            bldg_per_km2 = 0.0 if area_km2 == 0 else bldg_count / area_km2
            intxn_per_km2 = intersection_density_per_km2(roads, area_km2)

            hospitals = amen[amen.get("amenity") == "hospital"] if not amen.empty else amen
            schools   = amen[amen.get("amenity") == "school"] if not amen.empty else amen

            hosp_per_km2 = point_density_per_km2(hospitals, area_km2)
            school_per_km2 = point_density_per_km2(schools, area_km2)

            # ---------- DERIVED INDICES ----------
            infra    = 0.5 * norm_clip(road_km_per_km2, 0, 10) + 0.5 * norm_clip(intxn_per_km2, 0, 200)
            access   = 0.5 * norm_clip(hosp_per_km2, 0, 5) + 0.5 * norm_clip(school_per_km2, 0, 8)
            activity = 0.0  # placeholder for VIIRS or other activity metric
            green    = 0.0  # placeholder for green_ratio or NDVI-derived metric

            socio_score = 100.0 * (0.35 * infra + 0.35 * access + 0.20 * activity + 0.10 * green)

            # ---------- SUMMARY ----------
            osm_summary = {
                "area_km2": float(area_km2),
                "road_km": float(road_km),
                "road_km_per_km2": float(road_km_per_km2),
                "building_count": int(bldg_count),
                "buildings_per_km2": float(bldg_per_km2),
                "intersection_per_km2": float(intxn_per_km2),
                "hospitals_per_km2": float(hosp_per_km2),
                "schools_per_km2": float(school_per_km2),
                "infra_index": float(infra),
                "access_index": float(access),
                "socio_score": float(socio_score),
                "raw_counts": {
                    "roads_features": int(len(roads)) if hasattr(roads, "__len__") else None,
                    "building_features": int(len(build)) if hasattr(build, "__len__") else None,
                    "amenity_features": int(len(amen)) if hasattr(amen, "__len__") else None
                }
            }

            return {"osm_summary": osm_summary, "osm_status": "ok"}

        except Exception as e:
            return {"osm_summary": None, "osm_status": f"error: {e}"}

    def generate_gemini_insights(self, response: dict) -> dict:
        osm_summary = response.get("analysis", {}).get("osm_summary")
        if not osm_summary:
            return {"gemini_insights": None, "gemini_status": "no_osm_summary"}

        # If no Gemini model, return fallback quick summary
        if not self.gemini_model:
            # deterministic fallback (small, neutral)
            infra = osm_summary.get("infra_index")
            access = osm_summary.get("access_index")
            socio = osm_summary.get("socio_score")
            # small heuristics
            summary_text = (
                f"Synthesizing OSM metrics: infrastructure index={infra:.2f}, "
                f"access index={access:.2f}, socio score={socio:.1f}. "
                "This suggests moderate infrastructure with room to improve healthcare access."
            ) if infra is not None else "Insufficient data for automated insights."
            key_findings = [
                f"Road density ≈ {osm_summary.get('road_km_per_km2', 'N/A'):.2f} km/km²",
                f"Buildings/km² ≈ {osm_summary.get('buildings_per_km2', 'N/A'):.1f}",
                f"Socio score ≈ {socio:.1f}" if socio is not None else "Socio score not available"
            ]
            # use provided recommendations to create priority actions
            recs = response.get("recommendations", [])[:3]
            priority_actions = [f"Action: {r}" for r in recs] if recs else ["Review infrastructure and access metrics"]
            insights = {
                "summary_text": summary_text,
                "key_findings": key_findings,
                "priority_actions": priority_actions,
                "scores": {"infra_index": infra, "access_index": access, "socio_score": socio},
                "confidence": 0.45
            }
            return {"gemini_insights": insights, "gemini_status": "fallback_no_model"}

        # Build a concise, strict prompt asking Gemini to return JSON only
        classification = response.get("classification", {})
        recommendations = response.get("recommendations", [])
        location = response.get("location", {})

        prompt = f"""
            You are an expert urban analyst. Given the structured OSM-derived metrics and the user's query,
            produce a concise interpretation aligned with the classification and the recommendations.

            INPUT:
            - USER QUERY: {response.get('user_query')}
            - LOCATION: {location.get('name')} (type={location.get('type')}, coords={location.get('coordinates')})
            - CLASSIFICATION: category={classification.get('category')}, intent={classification.get('intent')}, priority={classification.get('priority')}
            - RECOMMENDATIONS: {recommendations}
            - OSM_SUMMARY (JSON): {json.dumps(osm_summary)}

            TASK:
            Return ONLY a single JSON object (no surrounding commentary) matching exactly this schema:

            {{
            "summary_text": "one to three sentences, plain english",
            "key_findings": ["short bullet 1", "short bullet 2", "..."],
            "priority_actions": ["actionable next step 1", "actionable next step 2"],
            "scores": {{
                "infra_index": number,
                "access_index": number,
                "socio_score": number
            }},
            "confidence": number   # 0.0-1.0 (your confidence in this interpretation)
            }}

            Rules:
            - Keep summary_text short and directly tied to OSM numbers (mention 1-2 metrics).
            - Key findings should be 3 bullets max.
            - Priority actions should reflect the provided recommendations and be actionable.
            - Confidence should be conservative (0.0-1.0).
            - Return valid JSON only. No extra text, no backticks.
            """

        try:
            resp = self.gemini_model.generate_content(prompt)
            response_text = getattr(resp, "text", str(resp)).strip()

            # Extract first JSON object from the model response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON object found in model output.")

            json_str = response_text[json_start:json_end]
            parsed = json.loads(json_str)

            # Basic validation and normalization of parsed result
            # Ensure scores are floats and confidence exists
            scores = parsed.get("scores", {})
            def as_float(v): 
                try: return float(v) 
                except Exception: return None
            parsed["scores"] = {
                "infra_index": as_float(scores.get("infra_index")),
                "access_index": as_float(scores.get("access_index")),
                "socio_score": as_float(scores.get("socio_score"))
            }
            parsed["confidence"] = as_float(parsed.get("confidence")) or 0.0
            # Guarantee lists
            parsed["key_findings"] = parsed.get("key_findings") or []
            parsed["priority_actions"] = parsed.get("priority_actions") or []
            return {"gemini_insights": parsed, "gemini_status": "ok"}

        except Exception as e:
            # Model failed or returned unparsable output -> safe fallback summary with error noted
            # Keep deterministic fallback similar to no-model case, but include error note
            infra = osm_summary.get("infra_index")
            access = osm_summary.get("access_index")
            socio = osm_summary.get("socio_score")
            summary_text = (
                f"Automatic interpretation failed (model error). Fallback: infra={infra}, access={access}, socio={socio}."
            )
            key_findings = [
                f"Road density ≈ {osm_summary.get('road_km_per_km2', 'N/A')}",
                f"Buildings/km² ≈ {osm_summary.get('buildings_per_km2', 'N/A')}"
            ]
            recs = response.get("recommendations", [])[:3]
            priority_actions = [f"Action: {r}" for r in recs] if recs else ["Review metrics"]
            fallback = {
                "summary_text": summary_text,
                "key_findings": key_findings,
                "priority_actions": priority_actions,
                "scores": {"infra_index": infra, "access_index": access, "socio_score": socio},
                "confidence": 0.2
            }
            return {"gemini_insights": fallback, "gemini_status": f"error: {e}"}



def process_query_once(query: str, gemini_api_key: Optional[str] = None, save: bool = False,
                       output_dir: str = "query_responses", verbose: bool = False) -> Dict[str, Any]:
    """
    One-line helper: process a single query and optionally save the response.
    """
    proc = SimpleQueryProcessor(gemini_api_key=gemini_api_key, verbose=verbose)
    result = proc.process_query(query)
    if save:
        proc.save_response(result, output_dir=output_dir)
    return result

def bbox_polygon(b):
    return Polygon([(b[0],b[1]), (b[2],b[1]), (b[2],b[2] if False else b[3]), (b[0],b[3])])

def osm_to_gdf(osm_json, geom_types=("way","node","relation")):
    feats = []
    for el in osm_json.get("elements", []):
        if el.get("type") not in geom_types: 
            continue
        tags = el.get("tags", {})
        if el["type"] == "node":
            geom = Point(el["lon"], el["lat"])
        elif el["type"] == "way":
            coords = [(n["lon"], n["lat"]) for n in el["geometry"]]
            geom = LineString(coords)
        else:
            # relations not handled fully; skip for now
            continue
        props = {"id": el["id"], **tags}
        feats.append({"geometry": geom, **props})
    if not feats:
        return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs="EPSG:4326")
    return gpd.GeoDataFrame(feats, geometry="geometry", crs="EPSG:4326")

def overpass(query, pause=2.0):
    url = "https://overpass-api.de/api/interpreter"
    r = requests.post(url, data={"data": query}, timeout=120)
    if r.status_code != 200:
        time.sleep(pause)
        r = requests.post(url, data={"data": query}, timeout=120)
    r.raise_for_status()
    return r.json()

def length_km(gdf):
    if gdf.empty: return 0.0
    g = gdf.to_crs(3857)
    return g.length.sum() / 1000.0

def intersection_density_per_km2(roads_gdf, area_km2):
    if roads_gdf.empty or area_km2 == 0:
        return 0.0

    # Crude intersections: count unique vertices occurring in >2 segments
    g = roads_gdf.to_crs(3857)
    pts = []
    for line in g.geometry:
        if line is None:
            continue
        if isinstance(line, LineString):  # Ensure the geometry is a LineString
            for x, y in zip(*line.xy):
                pts.append((round(x, 2), round(y, 2)))
        elif isinstance(line, Polygon):  # Handle Polygon geometries
            for x, y in zip(*line.exterior.xy):
                pts.append((round(x, 2), round(y, 2)))
    
    if not pts:
        return 0.0

    from collections import Counter
    c = Counter(pts)
    inter = sum(1 for k, v in c.items() if v >= 3)
    return inter / area_km2

def point_density_per_km2(gdf, area_km2):
    return 0.0 if gdf.empty or area_km2==0 else len(gdf)/area_km2

def norm_clip(x, a, b):
    return max(0.0, min(1.0, (x - a) / (b - a + 1e-9)))

