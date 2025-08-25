import { useState, useRef, useEffect } from "react";
import axios from "axios";

const UserIcon = ({ className = "w-6 h-6" }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M12 2C9.23858 2 7 4.23858 7 7C7 9.76142 9.23858 12 12 12C14.7614 12 17 9.76142 17 7C17 4.23858 14.7614 2 12 2Z"
      fill="currentColor"
    />
    <path
      d="M12 14C7.58172 14 4 17.5817 4 22H20C20 17.5817 16.4183 14 12 14Z"
      fill="currentColor"
    />
  </svg>
);

const ModelIcon = ({ className = "w-6 h-6" }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M12 3L4 9V21H20V9L12 3Z"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M12 14C14.2091 14 16 12.2091 16 10C16 7.79086 14.2091 6 12 6C9.79086 6 8 7.79086 8 10C8 12.2091 9.79086 14 12 14Z"
      stroke="currentColor"
      strokeWidth="2"
    />
    <path
      d="M12 14V21"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const SendIcon = ({ className = "w-6 h-6" }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M22 2L11 13"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M22 2L15 22L11 13L2 9L22 2Z"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const PlusIcon = ({ className = "w-5 h-5" }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M12 5V19"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M5 12H19"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const CopyIcon = ({ className = "w-4 h-4" }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <rect
      x="9"
      y="9"
      width="13"
      height="13"
      rx="2"
      ry="2"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M5 15H4C2.89543 15 2 14.1046 2 13V4C2 2.89543 2.89543 2 4 2H13C14.1046 2 15 2.89543 15 4V5"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const MenuIcon = ({ className = "w-6 h-6" }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M4 6H20M4 12H20M4 18H20"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const CopyButton = ({ text }) => {
  const [isCopied, setIsCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      className="absolute top-2 right-2 p-1.5 rounded-md text-zinc-400 hover:text-white hover:bg-white/10 transition-all duration-200"
    >
      {isCopied ? "Copied!" : <CopyIcon />}
    </button>
  );
};

const Message = ({ role, content }) => {
  const isModel = role === "model";
  return (
    <div className="group animate-fade-in-up">
      <div
        className={`flex items-start gap-4 max-w-4xl mx-auto p-4 rounded-xl relative ${
          isModel ? "bg-zinc-900/50 ring-1 ring-zinc-800" : ""
        }`}
      >
        <div
          className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-white ${
            isModel
              ? "bg-gradient-to-tr from-cyan-600 to-blue-600"
              : "bg-zinc-700"
          }`}
        >
          {isModel ? (
            <ModelIcon className="w-5 h-5" />
          ) : (
            <UserIcon className="w-5 h-5" />
          )}
        </div>
        <div className="flex-1 overflow-hidden pt-0.5">
          <div className="prose prose-invert prose-p:text-zinc-300 prose-p:leading-relaxed text-zinc-200">
            {content}
          </div>
        </div>
        {isModel && (
          <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-300">
            <CopyButton text={content} />
          </div>
        )}
      </div>
    </div>
  );
};

const TypingIndicator = () => (
  <div className="animate-fade-in-up">
    <div className="flex items-start gap-4 max-w-4xl mx-auto p-4">
      <div className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center bg-gradient-to-tr from-cyan-600 to-blue-600 text-white">
        <ModelIcon className="w-5 h-5" />
      </div>
      <div className="flex items-center space-x-1.5 pt-2.5">
        <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
        <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
        <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce"></div>
      </div>
    </div>
  </div>
);

function MetricCard({ label, value, unit = "" }) {
  const displayValue = typeof value === "number" ? value.toFixed(2) : value;
  return (
    <div className="bg-zinc-900/70 p-4 rounded-lg text-center shadow-lg">
      <p className="text-sm text-zinc-400 mb-1">{label}</p>
      <p className="text-2xl font-bold text-cyan-400">
        {displayValue}
        <span className="text-base font-normal text-zinc-500 ml-1">{unit}</span>
      </p>
    </div>
  );
}

function CustomResponse({ data }) {
  if (!data || !data.location || !data.gemini_insights) {
    return (
      <div className="text-red-400 bg-red-900/20 p-4 rounded-lg">
        Error: Received an invalid data format.
      </div>
    );
  }

  const { location, osm_summary, gemini_insights } = data;

  return (
    <div className="bg-black/30 backdrop-blur-md border border-white/10 rounded-xl p-6 space-y-6">
      <div className="border-b border-white/10 pb-4">
        <h2 className="text-2xl font-bold text-white">
          Analysis for <span className="text-cyan-400">{location.name}</span>
        </h2>
        <p className="text-sm text-zinc-400 uppercase tracking-wider">
          {location.type}
        </p>
      </div>
      <div>
        <p className="text-zinc-300 leading-relaxed">
          {gemini_insights.summary_text}
        </p>
      </div>
      <div>
        <h3 className="text-lg font-semibold text-zinc-200 mb-3">
          Key Findings
        </h3>
        <ul className="space-y-2 list-disc list-inside text-zinc-300">
          {gemini_insights.key_findings?.map((finding, index) => (
            <li key={index}>{finding}</li>
          ))}
        </ul>
      </div>
      <div>
        <h3 className="text-lg font-semibold text-zinc-200 mb-3">
          Core Metrics
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <MetricCard
            label="Infrastructure Index"
            value={osm_summary.infra_index}
          />
          <MetricCard label="Access Index" value={osm_summary.access_index} />
          <MetricCard label="Socio Score" value={osm_summary.socio_score} />
          <MetricCard
            label="Road Density"
            value={osm_summary.road_km_per_km2}
            unit="km/km²"
          />
          <MetricCard
            label="Building Density"
            value={osm_summary.buildings_per_km2}
            unit="bldgs/km²"
          />
          <MetricCard
            label="Total Buildings"
            value={osm_summary.building_count}
          />
        </div>
      </div>
    </div>
  );
}

// --- Main Chat Application Component (Updated) ---

export default function ChatApp() {
  const [messages, setMessages] = useState([
    {
      role: "model",
      type: "text",
      content: "Hello! I'm an AI assistant. How can I help you today?",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const fetchModelResponse = async (userMessage) => {
    try {
      const response = await axios.post(
        `${import.meta.env.VITE_API_URL}/send_query/`,
        {
          query: userMessage,
        }
      );
      return response.data;
    } catch (error) {
      console.error("API Error:", error);
      return {
        error: true,
        message: "Sorry, something went wrong. Please try again.",
      };
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = { role: "user", type: "text", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    const modelResponse = await fetchModelResponse(input);

    let newModelMessage;
    if (modelResponse.error) {
      newModelMessage = {
        role: "model",
        type: "text",
        content: modelResponse.message,
      };
    } else {
      newModelMessage = {
        role: "model",
        type: "custom",
        content: modelResponse,
      };
    }

    setMessages((prev) => [...prev, newModelMessage]);
    setIsLoading(false);
  };

  return (
    <div className="flex h-screen min-w-screen bg-zinc-950 text-zinc-200 font-sans overflow-hidden">
      {/* Background styles remain the same */}
      <div
        className="absolute inset-0 z-0 opacity-20"
        style={{
          backgroundImage:
            "radial-gradient(#444 1px, transparent 1px), radial-gradient(#444 1px, transparent 1px)",
          backgroundSize: "30px 30px",
          backgroundPosition: "0 0, 15px 15px",
        }}
      />
      <div className="absolute inset-0 z-0 bg-gradient-to-b from-transparent via-transparent to-black" />

      {/* --- Main Chat Area (Updated rendering logic) --- */}
      <main className="flex-1 flex flex-col z-10 relative">
        {/* <button
          onClick={() => setSidebarOpen(!isSidebarOpen)}
          className="md:absolute top-4 left-4 z-30 p-2 rounded-full bg-black/20 hover:bg-white/10 transition-colors hidden md:block"
        >
          <MenuIcon />
        </button> */}

        <div className="flex-1 overflow-y-auto p-4 md:p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {messages?.map((msg, index) => {
              if (msg.role === "user") {
                return (
                  <Message key={index} role={msg.role} content={msg.content} />
                );
              }
              // For the model, check the type
              if (msg.type === "custom") {
                return <CustomResponse key={index} data={msg.content} />;
              }
              // Fallback to the standard Message component for simple text
              return (
                <Message key={index} role={msg.role} content={msg.content} />
              );
            })}
            {isLoading && <TypingIndicator />}
            <div ref={chatEndRef} />
          </div>
        </div>

        {/* --- Prompt Input Area (unchanged) --- */}
        <div className="w-full p-4 md:p-6 flex justify-center items-center bg-gradient-to-t from-black/50 to-transparent">
          <form onSubmit={handleSendMessage} className="w-full max-w-4xl">
            <div className="relative flex items-center justify-center">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) handleSendMessage(e);
                }}
                placeholder="Ask me anything..."
                rows={1}
                className="w-full resize-none p-4 pr-16 text-lg rounded-xl bg-zinc-900/80 border-none ring-2 ring-zinc-800 focus:ring-cyan-500 focus:outline-none transition-all duration-300 shadow-2xl shadow-black/50 backdrop-blur-sm"
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="absolute right-2.5 bottom-2.5 p-2 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 text-white disabled:opacity-50 disabled:cursor-not-allowed hover:scale-110 active:scale-95 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-zinc-900 focus:ring-cyan-400"
              >
                <SendIcon />
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
