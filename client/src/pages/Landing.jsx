import { useState, useEffect, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Polygon,
  useMapEvents,
} from "react-leaflet";

import analyzeBBox from "../utils/script";

import L from "leaflet";
import "leaflet/dist/leaflet.css";

import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const DEFAULT_CENTER = [20.5937, 78.9629];
const DEFAULT_ZOOM = 5;
const MAX_POINTS = 4;

function MapClickHandler({ points, addPoint }) {
  useMapEvents({
    click(e) {
      if (points.length >= MAX_POINTS) return;
      const { lat, lng } = e.latlng;
      addPoint([lat, lng]);
    },
  });
  return null;
}

const findLongestDistance = (coordinates) => {
  // Check if we have at least 2 points
  if (coordinates.length < 2) {
    throw new Error("At least 2 coordinates are required");
  }

  let maxDistance = 0;
  let point1 = null;
  let point2 = null;

  // Calculate distance between all pairs of points
  for (let i = 0; i < coordinates.length; i++) {
    for (let j = i + 1; j < coordinates.length; j++) {
      const [lat1, lon1] = coordinates[i];
      const [lat2, lon2] = coordinates[j];

      // Calculate Euclidean distance
      const distance = Math.sqrt(
        Math.pow(lat2 - lat1, 2) + Math.pow(lon2 - lon1, 2)
      );

      // Update maximum distance and corresponding points
      if (distance > maxDistance) {
        maxDistance = distance;
        point1 = coordinates[i];
        point2 = coordinates[j];
      }
    }
  }

  // Return in bbox format: [lon, lat, lon, lat]
  const [lat1, lon1] = point1;
  const [lat2, lon2] = point2;

  return [lon1, lat1, lon2, lat2];
};

const Landing = () => {
  const mapRef = useRef(null);
  const [points, setPoints] = useState([]);
  const [activeTab, setActiveTab] = useState("controls");
  const [insights, setInsights] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleClick = async () => {
    setActiveTab("insights");
    setIsLoading(true);
    setInsights([]);

    const pts = findLongestDistance(points);
    const { metrics, analysis } = await analyzeBBox(pts);
    console.log(metrics);
    console.log(analysis);

    const results = [
      {
        type: "success",
        title: "Area Calculated",
        content:
          "The selected polygon covers an area of 45.8 square kilometers.",
      },
      {
        type: "info",
        title: "Population Density",
        content: "Estimated population density is 2,300 people per sq. km.",
      },
      {
        type: "warning",
        title: "Data Anomaly",
        content:
          "Elevation data for one point seems inconsistent with the surrounding area.",
      },
    ];

    setInsights(results);
    setIsLoading(false);
  };

  const addPoint = (latlng) => {
    setPoints((p) => {
      if (p.length >= MAX_POINTS) return p;
      return [...p, latlng];
    });
  };

  const onMarkerDragEnd = (e, index) => {
    const marker = e.target;
    const { lat, lng } = marker.getLatLng();
    setPoints((prev) => {
      const next = [...prev];
      next[index] = [lat, lng];
      return next;
    });
  };

  const removeLast = () => setPoints((p) => p.slice(0, -1));

  const clearAll = () => setPoints([]);

  useEffect(() => {
    localStorage.setItem("leaflet-points", JSON.stringify(points));
  }, [points]);

  useEffect(() => {
    const saved = JSON.parse(localStorage.getItem("leaflet-points") || "[]");
    if (Array.isArray(saved) && saved.length) setPoints(saved);
  }, []);

  return (
    <div className="h-screen min-w-screen flex bg-slate-900 text-slate-100 font-sans">
      {/* Main Map Area */}
      <main className="flex-1 relative">
        <MapContainer
          center={DEFAULT_CENTER}
          zoom={DEFAULT_ZOOM}
          style={{ height: "100%", width: "100%", backgroundColor: "#1a202c" }} // Set a dark bg for the map container
          whenCreated={(mapInstance) => (mapRef.current = mapInstance)}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />

          <MapClickHandler points={points} addPoint={addPoint} />

          {points.map((pt, i) => (
            <Marker
              key={i}
              position={pt}
              draggable={true}
              eventHandlers={{
                dragend: (e) => onMarkerDragEnd(e, i),
              }}
            />
          ))}

          {points.length >= 3 && (
            <Polygon
              positions={points}
              pathOptions={{
                fillColor: "#0891b2", // Using cyan accent
                fillOpacity: 0.2,
                color: "#06b6d4", // Brighter cyan for the border
                weight: 2,
              }}
            />
          )}
        </MapContainer>
      </main>

      {/* Control Panel / Sidebar */}
      <aside className="w-96 bg-black/50 backdrop-blur-xl border-l border-slate-700 flex flex-col shadow-2xl">
        {/* Header */}
        <div className="p-6 border-b border-slate-700/50">
          <h1 className="text-2xl font-bold text-cyan-400">Polygon Analyzer</h1>
          <p className="text-sm text-slate-400 mt-1">
            Define an area to get AI-powered insights.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="p-2 border-b border-slate-700/50 bg-slate-950/30">
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => setActiveTab("controls")}
              className={`px-3 py-2 rounded-md text-sm font-semibold transition-colors ${
                activeTab === "controls"
                  ? "bg-slate-700 text-cyan-300"
                  : "text-slate-400 hover:bg-slate-800/50"
              }`}
            >
              Controls
            </button>
            <button
              onClick={() => setActiveTab("insights")}
              className={`px-3 py-2 rounded-md text-sm font-semibold transition-colors ${
                activeTab === "insights"
                  ? "bg-slate-700 text-cyan-300"
                  : "text-slate-400 hover:bg-slate-800/50"
              }`}
            >
              Insights
            </button>
          </div>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto">
          {/* CONTROLS TAB */}
          {activeTab === "controls" && (
            <div className="p-6 space-y-3">
              <h2 className="text-sm font-semibold tracking-wider uppercase text-slate-400">
                Defined Points ({points.length}/{MAX_POINTS})
              </h2>
              {points.length > 0 ? (
                points.map((pt, i) => (
                  <div
                    key={i}
                    className="flex justify-between items-center bg-slate-800/50 p-3 rounded-lg border border-slate-700"
                  >
                    <div>
                      <div className="font-medium text-slate-200">
                        Point {i + 1}
                      </div>
                      <div className="text-xs text-slate-400 font-mono">
                        {pt[0].toFixed(4)}, {pt[1].toFixed(4)}
                      </div>
                    </div>
                    <button
                      onClick={() =>
                        setPoints((prev) => prev.filter((_, idx) => idx !== i))
                      }
                      className="p-2 text-slate-500 rounded-md hover:bg-red-500/20 hover:text-red-400 transition-colors"
                      aria-label="Delete point"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="h-4 w-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    </button>
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-slate-500 text-sm">
                  No points added yet.
                </div>
              )}
            </div>
          )}

          {/* INSIGHTS TAB */}
          {activeTab === "insights" && (
            <div className="p-6">
              {isLoading ? (
                <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-400">
                  <svg
                    className="animate-spin h-8 w-8 text-cyan-400"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  <span>Analyzing...</span>
                </div>
              ) : insights.length > 0 ? (
                <div className="space-y-4">
                  {insights.map((item, i) => (
                    <div
                      key={i}
                      className={`p-4 rounded-lg bg-slate-800/50 border border-slate-700 ${
                        item.type === "warning"
                          ? "border-l-4 border-l-yellow-400"
                          : item.type === "success"
                          ? "border-l-4 border-l-green-400"
                          : "border-l-4 border-l-cyan-400"
                      }`}
                    >
                      <h3 className="font-semibold text-slate-200">
                        {item.title}
                      </h3>
                      <p className="text-sm text-slate-400 mt-1">
                        {item.content}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500 text-sm">
                  Click "Analyze Polygon" to generate insights for the selected
                  area.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Sidebar Actions */}
        <div className="p-6 mt-auto border-t border-slate-700/50 bg-slate-950/30">
          <div className="grid grid-cols-2 gap-3 mb-4">
            <button
              onClick={removeLast}
              disabled={points.length === 0}
              className="px-3 py-2 rounded-md bg-slate-800 text-sm font-medium hover:bg-slate-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Undo Last
            </button>
            <button
              onClick={clearAll}
              className="px-3 py-2 rounded-md bg-red-500/20 text-red-400 text-sm font-medium hover:bg-red-500/30 transition-colors"
            >
              Clear All
            </button>
          </div>
          <button
            onClick={handleClick}
            disabled={points.length < 3 || isLoading}
            className="w-full py-3 rounded-lg bg-cyan-600 text-white font-bold text-lg transition-all hover:bg-cyan-500 active:scale-95 disabled:bg-slate-700 disabled:text-slate-400 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isLoading ? "Please Wait..." : "Analyze Polygon"}
          </button>
        </div>
      </aside>
    </div>
  );
};

export default Landing;
