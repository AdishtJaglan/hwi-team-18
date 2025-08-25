import { useState, useEffect, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Polygon,
  useMapEvents,
} from "react-leaflet";
import { GoogleGenerativeAI } from "@google/generative-ai";

import FloatingLLMNav from "../components/LLMicon";
import analyzeBBox from "../utils/script";

import L from "leaflet";
import "leaflet/dist/leaflet.css";

import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import { GoogleGenAI } from "@google/genai";

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

const MetricsDisplay = ({ metrics }) => {
  const displayMetrics = [
    { key: "area_km2", label: "Total Area", unit: "km²" },
    { key: "SocioEconScore", label: "Socio-Econ Score", unit: "/ 10" },
    { key: "roads_km", label: "Roads Length", unit: "km" },
    { key: "buildings_count", label: "Building Count", unit: "" },
    { key: "roads_km_per_km2", label: "Road Density", unit: "km/km²" },
    { key: "buildings_per_km2", label: "Building Density", unit: "per km²" },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 mt-3">
      {displayMetrics.map((metric) => (
        <div key={metric.key} className="group relative">
          {/* Subtle glow effect on hover */}
          <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-blue-500/5 rounded-xl blur opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

          <div className="relative bg-black/60 backdrop-blur-sm border border-slate-700/50 p-4 rounded-xl hover:border-cyan-400/30 transition-all duration-300">
            <div className="text-xs font-medium text-slate-400 mb-2 tracking-wide uppercase">
              {metric.label}
            </div>
            <div className="flex items-baseline space-x-1">
              <span className="text-xl font-bold text-white">
                {metrics[metric.key] !== undefined
                  ? Number(metrics[metric.key]).toFixed(2)
                  : "N/A"}
              </span>
              {metric.unit && (
                <span className="text-sm text-cyan-400 font-medium">
                  {metric.unit}
                </span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

const AnalysisDisplay = ({ text }) => {
  const formattedText = text?.split("\n")?.map((line, index) => {
    if (line.trim() === "") {
      return <div key={index} className="h-3" />; // Proper spacing for empty lines
    }

    const parts = line?.split("*").map((part, i) =>
      i % 2 === 1 ? (
        <strong key={i} className="text-cyan-300 font-semibold">
          {part}
        </strong>
      ) : (
        part
      )
    );

    return (
      <p key={index} className="mb-3 text-slate-200 leading-relaxed text-sm">
        {parts}
      </p>
    );
  });

  return <div className="mt-3">{formattedText}</div>;
};

const Landing = () => {
  const mapRef = useRef(null);
  const [points, setPoints] = useState([]);
  const [activeTab, setActiveTab] = useState("controls");
  const [insights, setInsights] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const [followUpPrompt, setFollowUpPrompt] = useState("");
  const [isFollowUpLoading, setIsFollowUpLoading] = useState(false);
  const [context, setContext] = useState([]);

  const handleClick = async () => {
    setActiveTab("insights");
    setIsLoading(true);
    setInsights([]);
    setContext([]);

    const pts = findLongestDistance(points);
    const { metrics, analysis } = await analyzeBBox(pts, {
      apiKey: import.meta.env.VITE_GEMINI_KEY,
    });

    setContext([...context, analysis]);

    const newInsights = [
      {
        id: "metrics",
        type: "metrics",
        title: "Key Metrics at a Glance",
        content: <MetricsDisplay metrics={metrics} />,
      },
      {
        id: "analysis",
        type: "analysis",
        title: "AI-Powered Analysis",
        content: <AnalysisDisplay text={analysis} />,
      },
    ];

    setInsights(newInsights);
    setIsLoading(false);
  };

  const handleFollowUp = async (e) => {
    e.preventDefault();
    if (!followUpPrompt.trim()) return;

    setIsFollowUpLoading(true);

    try {
      const apiKey = import.meta.env.VITE_GEMINI_KEY;
      if (!apiKey) {
        throw new Error("API key is missing.");
      }
      const ai = new GoogleGenAI({ apiKey });
      const fullPrompt = `
      Previous analysis context:
      ---
      ${context.join("\n\n")}
      ---
      Based on the context above, answer the following question. Do not refer to the prompt itself, just provide the answer as if continuing the conversation.
      Question: "${followUpPrompt}"
    `;
      const response = await ai.models.generateContent({
        model: "gemini-2.0-flash",
        contents: fullPrompt,
      });

      const cand = response?.candidates?.[0];
      const text = cand?.content?.parts?.[0]?.text ?? "";
      
      const newInsight = {
        id: `follow-up-${Date.now()}`,
        type: "analysis",
        title: `Follow-up: "${followUpPrompt}"`,
        content: <AnalysisDisplay text={text} />,
      };

      setInsights((prevInsights) => [...prevInsights, newInsight]);
      setContext((prevContext) => [...prevContext, text]);

      setFollowUpPrompt("");
    } catch (error) {
      console.error("Error calling Gemini API:", error?.message);
      alert("Sorry, there was an error processing your request.");
    } finally {
      setIsFollowUpLoading(false);
    }
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
    <div className="h-screen min-w-screen flex bg-black text-slate-100 font-sans">
      <FloatingLLMNav />
      {/* Main Map Area */}
      <main className="flex-1 relative z-20">
        <MapContainer
          center={DEFAULT_CENTER}
          zoom={DEFAULT_ZOOM}
          style={{ height: "100%", width: "100%", backgroundColor: "#0f0f0f" }}
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
                fillColor: "#06b6d4",
                fillOpacity: 0.15,
                color: "#22d3ee",
                weight: 2,
              }}
            />
          )}
        </MapContainer>
      </main>

      {/* Control Panel / Sidebar */}
      <aside className="w-96 bg-black/90 backdrop-blur-2xl border-l border-slate-700/30 flex flex-col shadow-2xl">
        {/* Header */}
        <div className="p-8 border-b border-slate-700/30">
          <div className="flex items-center space-x-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 backdrop-blur-sm border border-cyan-500/20 flex items-center justify-center">
              <svg
                className="w-5 h-5 text-cyan-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-white to-cyan-200 bg-clip-text text-transparent">
                Polygon Analyzer
              </h1>
            </div>
          </div>
          <p className="text-sm text-slate-400 leading-relaxed">
            Define geographical areas and unlock AI-powered insights about
            infrastructure, demographics, and spatial characteristics.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="p-6 border-b border-slate-700/30">
          <div className="relative bg-black/60 backdrop-blur-sm rounded-xl p-1 border border-slate-700/50">
            <div className="grid grid-cols-2 gap-1">
              <button
                onClick={() => setActiveTab("controls")}
                className={`relative px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-300 ${
                  activeTab === "controls"
                    ? "bg-gradient-to-r from-cyan-600/90 to-blue-600/90 text-white shadow-lg backdrop-blur-sm"
                    : "text-slate-400 hover:text-white hover:bg-white/5"
                }`}
              >
                Controls
              </button>
              <button
                onClick={() => setActiveTab("insights")}
                className={`relative px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-300 ${
                  activeTab === "insights"
                    ? "bg-gradient-to-r from-cyan-600/90 to-blue-600/90 text-white shadow-lg backdrop-blur-sm"
                    : "text-slate-400 hover:text-white hover:bg-white/5"
                }`}
              >
                Insights
                {insights.length > 0 && activeTab !== "insights" && (
                  <div className="absolute -top-1 -right-1 w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto">
          {/* CONTROLS TAB */}
          {activeTab === "controls" && (
            <div className="p-6 space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold tracking-wider uppercase text-slate-400">
                  Defined Points
                </h2>
                <div className="px-3 py-1 bg-black/60 backdrop-blur-sm rounded-full text-xs font-medium text-cyan-400 border border-cyan-500/20">
                  {points.length} / {MAX_POINTS}
                </div>
              </div>

              {points.length > 0 ? (
                <div className="space-y-3">
                  {points.map((pt, i) => (
                    <div
                      key={i}
                      className="group bg-black/60 backdrop-blur-sm border border-slate-700/50 p-4 rounded-xl hover:border-cyan-400/30 transition-all duration-300"
                    >
                      <div className="flex justify-between items-center">
                        <div className="flex items-center space-x-3">
                          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20 backdrop-blur-sm flex items-center justify-center border border-cyan-500/20">
                            <span className="text-sm font-bold text-cyan-400">
                              {i + 1}
                            </span>
                          </div>
                          <div>
                            <div className="font-medium text-slate-200 text-sm">
                              Point {i + 1}
                            </div>
                            <div className="text-xs text-slate-400 font-mono mt-0.5">
                              {pt[0].toFixed(4)}, {pt[1].toFixed(4)}
                            </div>
                          </div>
                        </div>
                        <button
                          onClick={() =>
                            setPoints((prev) =>
                              prev.filter((_, idx) => idx !== i)
                            )
                          }
                          className="opacity-0 group-hover:opacity-100 p-2 text-slate-500 rounded-lg hover:bg-red-500/20 hover:text-red-400 transition-all duration-200"
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
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 space-y-4">
                  <div className="w-16 h-16 mx-auto bg-black/60 backdrop-blur-sm rounded-2xl flex items-center justify-center border border-slate-700/50">
                    <svg
                      className="w-8 h-8 text-slate-500"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                  </div>
                  <div>
                    <p className="text-slate-400 text-sm font-medium mb-1">
                      No points defined yet
                    </p>
                    <p className="text-slate-500 text-xs">
                      Click anywhere on the map to add vertices
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* INSIGHTS TAB */}
          {activeTab === "insights" && (
            <div className="p-6 h-full flex flex-col">
              {isLoading ? (
                <div className="flex flex-col items-center justify-center h-full gap-6 py-20">
                  <div className="relative">
                    <div className="w-12 h-12 border-3 border-slate-700/50 rounded-full animate-pulse"></div>
                    <div className="absolute top-0 left-0 w-12 h-12 border-3 border-transparent border-t-cyan-400 rounded-full animate-spin"></div>
                  </div>
                  <div className="text-center space-y-2">
                    <p className="text-lg font-semibold text-white">
                      Analyzing Polygon
                    </p>
                    <p className="text-sm text-slate-400">
                      Processing geospatial intelligence...
                    </p>
                  </div>
                </div>
              ) : insights.length > 0 ? (
                <>
                  {/* Scrollable container for insights */}
                  <div className="flex-grow space-y-8 overflow-y-auto pr-2">
                    {insights.map((item) => (
                      <div key={item.id} className="space-y-4">
                        <div className="flex items-center space-x-3">
                          <div className="w-1.5 h-1.5 bg-gradient-to-r from-cyan-400 to-blue-400 rounded-full"></div>
                          <h3 className="text-lg font-semibold text-white">
                            {item.title}
                          </h3>
                        </div>
                        <div
                          className={`${
                            item.type === "analysis"
                              ? "bg-black/60 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6"
                              : ""
                          }`}
                        >
                          {item.content}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Follow-up Input Form */}
                  <div className="mt-6 pt-6 border-t border-slate-700/50">
                    <form onSubmit={handleFollowUp} className="relative">
                      <input
                        type="text"
                        value={followUpPrompt}
                        onChange={(e) => setFollowUpPrompt(e.target.value)}
                        placeholder="Ask a follow-up question..."
                        className="w-full bg-slate-900/80 border border-slate-700/50 rounded-lg py-3 pl-4 pr-14 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-400 transition-all"
                        disabled={isFollowUpLoading}
                      />
                      <button
                        type="submit"
                        className="absolute inset-y-0 right-0 flex items-center justify-center w-14 text-slate-400 hover:text-cyan-400 disabled:text-slate-600 disabled:cursor-not-allowed transition-colors"
                        disabled={isFollowUpLoading || !followUpPrompt.trim()}
                      >
                        {isFollowUpLoading ? (
                          <div className="w-5 h-5 border-2 border-slate-500 border-t-cyan-400 rounded-full animate-spin"></div>
                        ) : (
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            className="h-6 w-6"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <path d="M5 12h14"></path>
                            <path d="m12 5 7 7-7 7"></path>
                          </svg>
                        )}
                      </button>
                    </form>
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center h-full gap-6 py-20">
                  <div className="w-20 h-20 bg-black/60 backdrop-blur-sm rounded-2xl flex items-center justify-center border border-slate-700/50">
                    <svg
                      className="w-10 h-10 text-slate-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                      />
                    </svg>
                  </div>
                  <div className="text-center max-w-sm space-y-2">
                    <p className="text-white font-semibold">
                      Ready for Analysis
                    </p>
                    <p className="text-sm text-slate-400 leading-relaxed">
                      Create a polygon with at least 3 points and click "Analyze
                      Polygon" to generate comprehensive insights.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Sidebar Actions */}
        <div className="p-6 mt-auto border-t border-slate-700/30 bg-black/40 backdrop-blur-sm">
          <div className="grid grid-cols-2 gap-3 mb-6">
            <button
              onClick={removeLast}
              disabled={points.length === 0}
              className="px-3 py-3 rounded-xl bg-black/60 backdrop-blur-sm border border-slate-700/50 text-sm font-medium hover:bg-slate-800/50 hover:border-slate-600/50 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Undo Last
            </button>
            <button
              onClick={clearAll}
              className="px-3 py-3 rounded-xl bg-red-500/10 backdrop-blur-sm border border-red-500/20 text-red-400 text-sm font-medium hover:bg-red-500/20 hover:border-red-500/30 transition-all duration-200"
            >
              Clear All
            </button>
          </div>
          <button
            onClick={handleClick}
            disabled={points.length < 3 || isLoading}
            className="w-full py-4 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 text-white font-bold text-lg transition-all duration-300 hover:from-cyan-500 hover:to-blue-500 active:scale-95 disabled:from-slate-700 disabled:to-slate-700 disabled:text-slate-400 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg disabled:shadow-none backdrop-blur-sm"
          >
            {isLoading ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 10V3L4 14h7v7l9-11h-7z"
                  />
                </svg>
                <span>Analyze Polygon</span>
              </>
            )}
          </button>

          {points.length > 0 && points.length < 3 && (
            <p className="text-xs text-slate-500 text-center mt-3">
              Add {3 - points.length} more point
              {3 - points.length > 1 ? "s" : ""} to enable analysis
            </p>
          )}
        </div>
      </aside>
    </div>
  );
};

export default Landing;
