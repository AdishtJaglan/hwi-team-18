import { useState } from "react";
import { useNavigate } from "react-router-dom";

const FloatingLLMNav = () => {
  const navigate = useNavigate();
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div className="fixed bottom-6 left-6 z-50">
      {/* Tooltip */}
      {isHovered && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-3 px-3 py-1.5 bg-black/90 backdrop-blur-sm border border-slate-600/50 rounded-lg text-xs font-medium text-white whitespace-nowrap">
          AI Assistant
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-2 border-r-2 border-t-2 border-transparent border-t-slate-600/50"></div>
        </div>
      )}

      {/* Main Button */}
      <button
        onClick={() => navigate("/bot")}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className="relative w-12 h-12 bg-black/70 backdrop-blur-sm border border-slate-600/30 rounded-xl shadow-lg hover:bg-black/80 hover:border-cyan-400/50 hover:shadow-cyan-500/20 hover:shadow-lg transition-all duration-300 active:scale-95 group"
      >
        {/* Icon */}
        <svg
          className="w-6 h-6 text-slate-400 group-hover:text-cyan-400 transition-colors duration-200 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z"
          />
        </svg>
      </button>
    </div>
  );
};

export default FloatingLLMNav;
