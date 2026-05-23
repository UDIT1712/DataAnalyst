import React, { useEffect, useRef, useState } from "react";
import {
  Send,
  Square,
  Loader2,
  ChevronDown,
  ChevronUp,
  Wrench,
  Bot,
  User,
} from "lucide-react";
import type { ChatMessage, ToolCall } from "@/types";

interface Props {
  messages: ChatMessage[];
  isStreaming: boolean;
  activeTools: ToolCall[];
  onSend: (text: string) => void;
  onStop: () => void;
  suggestions?: string[];
}

export function ChatInterface({
  messages,
  isStreaming,
  activeTools,
  onSend,
  onStop,
  suggestions = [],
}: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  function handleSend() {
    const text = input.trim();
    if (!text || isStreaming) return;
    onSend(text);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function autoResize(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scrollbar-thin">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4 opacity-60">
            <Bot size={48} className="text-brand-500" />
            <p className="text-lg font-semibold text-white">Data Analyst Agent</p>
            <p className="text-sm text-slate-400 max-w-xs">
              Upload a file or connect a database, then ask me anything about your data.
            </p>
            {suggestions.length > 0 && (
              <div className="flex flex-wrap gap-2 justify-center mt-2">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => onSend(s)}
                    className="text-xs bg-surface-secondary border border-slate-700 hover:border-brand-500 text-slate-300 rounded-full px-3 py-1 transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isStreaming && activeTools.length > 0 && (
          <div className="flex gap-2 items-start">
            <div className="w-7 h-7 rounded-full bg-brand-600 flex items-center justify-center shrink-0 mt-0.5">
              <Bot size={14} className="text-white" />
            </div>
            <div className="bg-surface-secondary rounded-xl p-3 space-y-1 max-w-sm">
              {activeTools
                .filter((t) => t.status === "running")
                .map((t) => (
                  <div key={t.id} className="flex items-center gap-2 text-xs text-slate-400">
                    <Loader2 size={12} className="animate-spin text-brand-400" />
                    <span className="font-mono">{t.name}</span>
                  </div>
                ))}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-slate-700 p-3 bg-surface-primary">
        <div className="flex gap-2 items-end bg-surface-secondary rounded-xl border border-slate-700 focus-within:border-brand-500 transition-colors p-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={autoResize}
            onKeyDown={handleKey}
            placeholder="Ask about your data..."
            rows={1}
            className="flex-1 bg-transparent text-white text-sm placeholder-slate-500 resize-none outline-none leading-relaxed max-h-40"
          />
          <button
            onClick={isStreaming ? onStop : handleSend}
            disabled={!isStreaming && !input.trim()}
            className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
              isStreaming
                ? "bg-red-500 hover:bg-red-600 text-white"
                : input.trim()
                ? "bg-brand-600 hover:bg-brand-700 text-white"
                : "bg-slate-700 text-slate-500 cursor-not-allowed"
            }`}
          >
            {isStreaming ? <Square size={14} /> : <Send size={14} />}
          </button>
        </div>
        <p className="text-xs text-slate-600 mt-1 text-center">
          Shift+Enter for new line · Enter to send
        </p>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const [toolsExpanded, setToolsExpanded] = useState(false);
  const completedTools = message.toolCalls?.filter((t) => t.status === "done") ?? [];

  return (
    <div className={`flex gap-2 items-start ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      <div
        className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
          isUser ? "bg-slate-600" : "bg-brand-600"
        }`}
      >
        {isUser ? <User size={14} className="text-white" /> : <Bot size={14} className="text-white" />}
      </div>

      <div className={`max-w-[80%] space-y-1 ${isUser ? "items-end" : "items-start"} flex flex-col`}>
        {/* Tool calls */}
        {completedTools.length > 0 && (
          <div className="w-full">
            <button
              onClick={() => setToolsExpanded((p) => !p)}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
            >
              <Wrench size={11} />
              {completedTools.length} tool{completedTools.length > 1 ? "s" : ""} used
              {toolsExpanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
            </button>
            {toolsExpanded && (
              <div className="mt-1 space-y-1">
                {completedTools.map((tc) => (
                  <div
                    key={tc.id}
                    className="bg-surface-tertiary rounded-lg px-2 py-1 text-xs font-mono text-slate-400"
                  >
                    <span className="text-brand-400">{tc.name}</span>
                    {tc.args && (
                      <span className="text-slate-500 ml-1 truncate block max-w-xs">
                        {tc.args.slice(0, 120)}
                        {tc.args.length > 120 ? "…" : ""}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Message content */}
        {message.content && (
          <div
            className={`rounded-xl px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap ${
              isUser
                ? "bg-brand-600 text-white rounded-tr-none"
                : "bg-surface-secondary text-slate-200 rounded-tl-none"
            }`}
          >
            <MarkdownText text={message.content} />
          </div>
        )}
      </div>
    </div>
  );
}

function MarkdownText({ text }: { text: string }) {
  // Simple inline markdown: **bold**, `code`, newlines
  const lines = text.split("\n");
  return (
    <>
      {lines.map((line, i) => {
        const parts = line.split(/(\*\*.*?\*\*|`.*?`)/g);
        return (
          <span key={i}>
            {parts.map((part, j) => {
              if (part.startsWith("**") && part.endsWith("**")) {
                return <strong key={j}>{part.slice(2, -2)}</strong>;
              }
              if (part.startsWith("`") && part.endsWith("`")) {
                return (
                  <code key={j} className="bg-surface-primary rounded px-1 font-mono text-xs text-brand-300">
                    {part.slice(1, -1)}
                  </code>
                );
              }
              return part;
            })}
            {i < lines.length - 1 && <br />}
          </span>
        );
      })}
    </>
  );
}
