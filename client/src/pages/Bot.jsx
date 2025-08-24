import { useState, useRef, useEffect } from "react";

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

export default function ChatApp() {
  const [messages, setMessages] = useState([
    {
      role: "model",
      content: "Hello! I'm an AI assistant. How can I help you today?",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setSidebarOpen] = useState(true);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const fetchModelResponse = async (userMessage) => {
    return new Promise((resolve) => {
      setTimeout(() => {
        const lowerCaseMessage = userMessage.toLowerCase();
        let response = `I've processed your request: "${userMessage}". As a demo, I provide canned responses. For a real application, I would connect to a powerful language model to give you a detailed and accurate answer.`;

        if (lowerCaseMessage.includes("react")) {
          response =
            "React is a popular open-source JavaScript library for building user interfaces, particularly for single-page applications. It allows developers to create reusable UI components and manage application state efficiently. It was created by Facebook and is now maintained by a community of developers.";
        } else if (
          lowerCaseMessage.includes("hello") ||
          lowerCaseMessage.includes("hi")
        ) {
          response = "Hello there! It's great to connect. What's on your mind?";
        } else if (lowerCaseMessage.includes("tailwind")) {
          response =
            "Tailwind CSS is a utility-first CSS framework for rapidly building custom user interfaces. Unlike other frameworks that come with pre-styled components, Tailwind provides low-level utility classes that let you build completely custom designs without ever leaving your HTML.";
        }
        resolve(response);
      }, 1500);
    });
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    const modelResponse = await fetchModelResponse(input);
    setMessages((prev) => [...prev, { role: "model", content: modelResponse }]);
    setIsLoading(false);
  };

  return (
    <div className="flex h-screen min-w-screen bg-zinc-950 text-zinc-200 font-sans overflow-hidden">
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

      {/* --- Collapsible Sidebar --- */}
      <aside
        className={`md:flex flex-col bg-black/30 backdrop-blur-lg border-r border-white/5 z-20 transition-all duration-300 ease-in-out overflow-hidden ${
          isSidebarOpen ? "w-72 p-4" : "w-0 p-0"
        }`}
      >
        <button className="flex items-center justify-center gap-2 w-full p-3 mb-6 rounded-lg text-lg font-semibold bg-gradient-to-r from-cyan-500 to-blue-500 text-white hover:opacity-90 transition-opacity">
          <PlusIcon /> New Chat
        </button>
        <nav className="flex-1 space-y-2">
          <a
            href="#"
            className="flex items-center p-3 text-zinc-300 rounded-lg bg-white/5 font-medium truncate"
          >
            React & Tailwind UI
          </a>
          <a
            href="#"
            className="flex items-center p-3 text-zinc-400 rounded-lg hover:bg-white/5 transition-colors truncate"
          >
            Collapsible Sidebar Logic
          </a>
        </nav>
      </aside>

      {/* --- Main Chat Area --- */}
      <main className="flex-1 flex flex-col z-10 relative">
        <button
          onClick={() => setSidebarOpen(!isSidebarOpen)}
          className="md:absolute top-4 left-4 z-30 p-2 rounded-full bg-black/20 hover:bg-white/10 transition-colors hidden md:block"
        >
          <MenuIcon />
        </button>

        <div className="flex-1 overflow-y-auto p-4 md:p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.map((msg, index) => (
              <Message key={index} role={msg.role} content={msg.content} />
            ))}
            {isLoading && <TypingIndicator />}
            <div ref={chatEndRef} />
          </div>
        </div>

        {/* --- Prompt Input Area --- */}
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
