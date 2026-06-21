"use client";

import { useState, useEffect, useRef } from "react";
import { User, Bot, Headset, Send, CheckCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { sendOperatorMessageAction, resolveConversationAction } from "../conversations/actions";

type Message = {
  id: string;
  role: "customer" | "agent" | "operator";
  content: string;
  createdAt: string;
  sources?: string[];
  confidence?: number | null;
};

type OperatorConsoleProps = {
  conversationId: string;
  messages: Message[];
  status: string;
};

export function OperatorConsole({ conversationId, messages, status }: OperatorConsoleProps) {
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isResolving, setIsResolving] = useState(false);
  const router = useRouter();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const interval = setInterval(() => {
      router.refresh();
    }, 5000); // 5 seconds polling
    return () => clearInterval(interval);
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isSending) return;

    setIsSending(true);
    const result = await sendOperatorMessageAction(conversationId, input);
    setIsSending(false);

    if (result.success) {
      setInput("");
    } else {
      alert(result.error);
    }
  }

  async function handleResolve() {
    if (isResolving) return;
    setIsResolving(true);
    const result = await resolveConversationAction(conversationId);
    setIsResolving(false);
    if (!result.success) {
      alert(result.error);
    }
  }

  return (
    <section className="bg-zinc-900/50 border border-white/5 rounded-xl overflow-hidden flex flex-col h-[600px]">
      <div className="p-6 border-b border-white/5 flex items-center justify-between bg-zinc-950/50">
        <div>
          <h2 className="text-lg font-semibold text-white">Transcript & Operator Inbox</h2>
          <p className="text-sm text-zinc-400">Messages, source attribution и operator events.</p>
        </div>
        {status !== "resolved" && (
          <button
            onClick={handleResolve}
            disabled={isResolving}
            className="flex items-center gap-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-4 py-2 rounded-lg text-sm font-medium hover:bg-emerald-500/20 transition-colors disabled:opacity-50"
          >
            <CheckCircle className="w-4 h-4" />
            {isResolving ? "Resolving..." : "Resolve"}
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((message) => (
          <article
            key={message.id}
            className={`flex gap-3 ${message.role === "customer" ? "" : "flex-row-reverse"}`}
          >
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                message.role === "customer"
                  ? "bg-blue-500/10 text-blue-400"
                  : message.role === "operator"
                  ? "bg-purple-500/10 text-purple-400"
                  : "bg-emerald-500/10 text-emerald-400"
              }`}
            >
              {message.role === "customer" ? (
                <User className="w-4 h-4" />
              ) : message.role === "operator" ? (
                <Headset className="w-4 h-4" />
              ) : (
                <Bot className="w-4 h-4" />
              )}
            </div>
            <div className={`flex-1 max-w-[80%] ${message.role === "customer" ? "" : "text-right"}`}>
              <div
                className={`inline-block rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  message.role === "customer"
                    ? "bg-blue-500/10 text-zinc-200 rounded-tl-sm"
                    : message.role === "operator"
                    ? "bg-purple-500/10 text-zinc-200 rounded-tr-sm"
                    : "bg-zinc-800 text-zinc-200 rounded-tr-sm"
                }`}
              >
                {message.content}
              </div>
              <div
                className={`flex items-center gap-2 mt-1.5 text-xs text-zinc-600 ${
                  message.role === "customer" ? "" : "justify-end"
                }`}
              >
                <span className="font-medium capitalize">{message.role}</span>
                <span>·</span>
                <span>{message.createdAt}</span>
              </div>
              {message.sources && message.sources.length > 0 ? (
                <div
                  className={`flex gap-1.5 mt-2 flex-wrap ${
                    message.role === "customer" ? "" : "justify-end"
                  }`}
                >
                  {message.sources.map((source) => (
                    <span
                      key={source}
                      className="inline-flex items-center px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] font-mono"
                      title="Использованный источник из Базы Знаний"
                    >
                      {source}
                    </span>
                  ))}
                  {message.confidence !== undefined && message.confidence !== null && (
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono ${
                        message.confidence > 0.7 
                          ? 'bg-emerald-500/10 text-emerald-400' 
                          : message.confidence > 0.4
                            ? 'bg-amber-500/10 text-amber-400'
                            : 'bg-rose-500/10 text-rose-400'
                      }`}
                      title="Уверенность LLM (Cosine Distance RAG)"
                    >
                      conf: {(message.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              ) : null}
            </div>
          </article>
        ))}
        <div ref={bottomRef} />
      </div>

      {status !== "resolved" && (
        <div className="p-4 border-t border-white/5 bg-zinc-950/50">
          <form onSubmit={handleSend} className="relative flex items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Введите сообщение от имени оператора..."
              className="w-full bg-black border border-white/10 rounded-xl pl-4 pr-12 py-3 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all"
            />
            <button
              type="submit"
              disabled={!input.trim() || isSending}
              className="absolute right-2 p-2 text-zinc-400 hover:text-purple-400 disabled:opacity-50 transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      )}
    </section>
  );
}
