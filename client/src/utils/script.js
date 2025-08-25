import axios from "axios";
import { polygon, lineString, length, area } from "@turf/turf";
import { GoogleGenAI } from "@google/genai";

/**
 * Module: script.js
 * Exported function: analyzeBBox(bbox, options)
 *
 * Purpose: given a bbox [minLon, minLat, maxLon, maxLat], this function
 * performs OSM queries (Overpass), computes infrastructure metrics,
 * optionally queries Gemini (Google) for a narrative analysis, and writes
 * out JSON/text/HTML map files into an output directory.
 *
 * Usage:
 *   import analyzeBBox from './socio_bbox_module.js';
 *   const bbox = [77.1, 28.55, 77.3, 28.75];
 *   await analyzeBBox(bbox, { apiKey: process.env.GOOGLE_API_KEY, outDir: './out' });
 */

function bboxPolygon(b) {
  const [minLon, minLat, maxLon, maxLat] = b;
  return polygon([
    [
      [minLon, minLat],
      [maxLon, minLat],
      [maxLon, maxLat],
      [minLon, maxLat],
      [minLon, minLat],
    ],
  ]);
}

async function overpass(query, retries = 1, pauseMs = 1500) {
  const url = "https://overpass-api.de/api/interpreter";
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const r = await axios.post(url, query, {
        timeout: 120000,
        headers: { "Content-Type": "text/plain" },
      });
      return r.data;
    } catch (err) {
      if (attempt < retries) {
        await new Promise((res) => setTimeout(res, pauseMs));
      } else {
        throw err;
      }
    }
  }
}

function osmToGeoJSON(osmJson, geomTypes = ["way", "node", "relation"]) {
  const features = [];
  for (const el of osmJson.elements || []) {
    if (!geomTypes.includes(el.type)) continue;
    const props = { id: el.id, ...(el.tags || {}) };
    if (el.type === "node") {
      features.push({
        type: "Feature",
        geometry: { type: "Point", coordinates: [el.lon, el.lat] },
        properties: props,
      });
    } else if (el.type === "way" && Array.isArray(el.geometry)) {
      const coords = el.geometry.map((g) => [g.lon, g.lat]);
      const geom = props.building
        ? { type: "Polygon", coordinates: [[...coords, coords[0]]] }
        : { type: "LineString", coordinates: coords };
      features.push({ type: "Feature", geometry: geom, properties: props });
    } else if (el.type === "relation") {
      // skipping complex relations for simplicity
      continue;
    }
  }
  return { type: "FeatureCollection", features };
}

function lengthKm(featureCollection) {
  if (
    !featureCollection ||
    !featureCollection.features ||
    featureCollection.features.length === 0
  )
    return 0.0;
  let total = 0;
  for (const f of featureCollection.features) {
    if (!f.geometry) continue;
    if (
      f.geometry.type === "LineString" ||
      f.geometry.type === "MultiLineString"
    ) {
      total += length(f, { units: "kilometers" });
    } else if (
      f.geometry.type === "Polygon" ||
      f.geometry.type === "MultiPolygon"
    ) {
      const polygons =
        f.geometry.type === "Polygon"
          ? [f.geometry.coordinates]
          : f.geometry.coordinates;
      for (const ring of polygons) {
        const ringLine = lineString(ring[0]);
        total += length(ringLine, { units: "kilometers" });
      }
    }
  }
  return total;
}

function pointDensityPerKm2(featureCollection, areaKm2) {
  if (!featureCollection || areaKm2 === 0) return 0.0;
  return (featureCollection.features || []).length / areaKm2;
}

function intersectionDensityPerKm2(roadsFeatureCollection, areaKm2) {
  if (!roadsFeatureCollection || areaKm2 === 0) return 0.0;
  const pts = [];
  for (const f of roadsFeatureCollection.features) {
    if (!f.geometry) continue;
    if (f.geometry.type === "LineString") {
      for (const [lon, lat] of f.geometry.coordinates) {
        const rx = Math.round(lon * 10000);
        const ry = Math.round(lat * 10000);
        pts.push(`${rx},${ry}`);
      }
    } else if (f.geometry.type === "MultiLineString") {
      for (const line of f.geometry.coordinates)
        for (const [lon, lat] of line) {
          const rx = Math.round(lon * 10000);
          const ry = Math.round(lat * 10000);
          pts.push(`${rx},${ry}`);
        }
    }
  }
  if (pts.length === 0) return 0.0;
  const counts = pts.reduce((acc, k) => {
    acc[k] = (acc[k] || 0) + 1;
    return acc;
  }, {});
  const intersections = Object.values(counts).filter((v) => v >= 3).length;
  return intersections / areaKm2;
}

function normClip(x, a, b) {
  return Math.max(0.0, Math.min(1.0, (x - a) / (b - a + 1e-9)));
}

// ----------------------- Gemini helper -----------------------
async function generateGeminiAnalysis(ai, metrics, model = "gemini-2.0-flash") {
  if (!ai)
    return "Gemini AI analysis not configured. Provide apiKey or set useGemini=false.";

  const prompt = `
You are an urban planning expert analyzing satellite data for infrastructure development.

Analyze this area based on the following metrics and provide insights in simple, engaging language:

AREA OVERVIEW:
- Geographic Area: ${metrics.area_km2} km²
- Location: Bounding box coordinates ${JSON.stringify(metrics.bbox)}

INFRASTRUCTURE METRICS:
- Road Density: ${metrics.roads_km_per_km2} km/km²
- Total Roads: ${metrics.roads_km} km
- Building Count: ${metrics.buildings_count}
- Building Density: ${metrics.buildings_per_km2} buildings/km²
- Intersection Density: ${metrics.intersections_per_km2} intersections/km²

SERVICE AVAILABILITY:
- Hospital Density: ${metrics.hospitals_per_km2} hospitals/km²
- School Density: ${metrics.schools_per_km2} schools/km²
- Overall Socio-Economic Score: ${metrics.SocioEconScore}/100

Please provide:
1. Infrastructure Development Status
2. Quality of Life Assessment
3. Road Network Analysis
4. Commercial & Industrial Potential
5. Community Services evaluation
6. Clear, actionable recommendations for future development.

Write as if you're explaining to a community leader. Keep it simple and practical.
  `;

  try {
    const response = await ai.models.generateContent({
      model,
      contents: prompt,
    });
    if (response?.text) return response.text;
    const cand = response?.candidates?.[0];
    const partText = cand?.content?.[0]?.parts?.[0]?.text;
    if (partText) return partText;
    if (typeof response === "string") return response;
    return JSON.stringify(response, null, 2);
  } catch (err) {
    console.error("⚠️ Gemini API error:", err?.message ?? err);
    return "Gemini AI analysis unavailable - using enhanced text analysis instead.";
  }
}

// ----------------------- Main exported function -----------------------
export async function analyzeBBox(bbox, options = {}) {
  const {
    apiKey = "",
    useGemini = true,
    overpassRetries = 1,
    model = "gemini-2.0-flash",
  } = options;

  if (!Array.isArray(bbox) || bbox.length !== 4) {
    throw new Error("bbox must be an array [minLon, minLat, maxLon, maxLat]");
  }

  // prepare AI client if requested
  let ai = null;
  if (useGemini) {
    if (!apiKey) {
      console.warn(
        "useGemini is true but no apiKey provided. Proceeding without Gemini."
      );
    } else {
      ai = new GoogleGenAI({ apiKey });
    }
  }

  const [minlon, minlat, maxlon, maxlat] = bbox;
  const Q_BASE = `(${minlat},${minlon},${maxlat},${maxlon})`;

  const Q_ROADS = `[out:json][timeout:60];way${Q_BASE}[highway];out geom;`;
  const Q_BUILD = `[out:json][timeout:60];way${Q_BASE}[building];out geom;`;
  const Q_AMEN = `[out:json][timeout:60];(node${Q_BASE}[amenity=hospital];node${Q_BASE}[amenity=clinic];node${Q_BASE}[amenity=school];node${Q_BASE}[amenity=university];node${Q_BASE}[public_transport=station];node${Q_BASE}[highway=bus_stop];);out body;`;

  // fetch OSM data
  const [roadsOs, buildOs, amenOs] = await Promise.all([
    overpass(Q_ROADS, overpassRetries),
    overpass(Q_BUILD, overpassRetries),
    overpass(Q_AMEN, overpassRetries),
  ]);

  const roadsGeo = osmToGeoJSON(roadsOs, ["way"]);
  const buildGeo = osmToGeoJSON(buildOs, ["way"]);
  const amenGeo = osmToGeoJSON(amenOs, ["node"]);

  const aoi = bboxPolygon(bbox);
  const areaKm2 = area(aoi) / 1e6;

  const road_km = lengthKm(roadsGeo);
  const road_km_per_km2 = areaKm2 === 0 ? 0 : road_km / areaKm2;
  const bldg_count = (buildGeo.features || []).length;
  const bldg_per_km2 = areaKm2 === 0 ? 0 : bldg_count / areaKm2;
  const intxn_per_km2 = intersectionDensityPerKm2(roadsGeo, areaKm2);

  const hospitals = {
    type: "FeatureCollection",
    features: (amenGeo.features || []).filter(
      (f) => (f.properties.amenity || "").toLowerCase() === "hospital"
    ),
  };
  const schools = {
    type: "FeatureCollection",
    features: (amenGeo.features || []).filter(
      (f) => (f.properties.amenity || "").toLowerCase() === "school"
    ),
  };

  const hosp_per_km2 = pointDensityPerKm2(hospitals, areaKm2);
  const school_per_km2 = pointDensityPerKm2(schools, areaKm2);

  const infra =
    0.5 * normClip(road_km_per_km2, 0, 10) +
    0.5 * normClip(intxn_per_km2, 0, 200);
  const access =
    0.5 * normClip(hosp_per_km2, 0, 5) + 0.5 * normClip(school_per_km2, 0, 8);
  const activity = 0.0;
  const green = 0.0;
  const socio_score =
    100.0 * (0.35 * infra + 0.35 * access + 0.2 * activity + 0.1 * green);

  const metrics = {
    area_km2: Number(areaKm2.toFixed(3)),
    roads_km: Number(road_km.toFixed(3)),
    roads_km_per_km2: Number(road_km_per_km2.toFixed(3)),
    buildings_count: bldg_count,
    buildings_per_km2: Number(bldg_per_km2.toFixed(3)),
    intersections_per_km2: Number(intxn_per_km2.toFixed(3)),
    hospitals_per_km2: Number(hosp_per_km2.toFixed(4)),
    schools_per_km2: Number(school_per_km2.toFixed(4)),
    SocioEconScore: Number(socio_score.toFixed(1)),
  };

  const gemini_analysis = await generateGeminiAnalysis(ai, metrics, model);

  return {
    metrics,
    analysis: gemini_analysis,
  };
}

export default analyzeBBox;
