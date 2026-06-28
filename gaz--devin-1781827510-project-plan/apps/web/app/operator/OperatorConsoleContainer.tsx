"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { MessageSquare, Send, User, Bot, Headset, Loader2, Wifi, WifiOff } from "lucide-react";
import { sendOperatorMessageAction, resolveConversationAction, handoffConversationAction } from "../conversations/actions";
import { DashboardShell } from "../components/DashboardShell";
import { toast } from "sonner";
import type { ConversationSummary, ConversationDetail } from "../../lib/mvp-data";

type OperatorConsoleContainerProps = {
  initialConversations: ConversationSummary[];
};

export function OperatorConsoleContainer({ initialConversations }: OperatorConsoleContainerProps) {
  const [conversations, setConversations] = useState<ConversationSummary[]>(initialConversations);
  const [selectedId, setSelectedId] = useState<string | null>(
    initialConversations.length > 0 ? initialConversations[0].id : null
  );
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isResolving, setIsResolving] = useState(false);
  const [isHandoff, setIsHandoff] = useState(false);
  const [filter, setFilter] = useState<"all" | "open" | "escalated">("all");

  const bottomRef = useRef<HTMLDivElement>(null);

  const [wsConnected, setWsConnected] = useState(false);

  const fetchConversations = useCallback(async () => {
    try {
      const res = await fetch("/api/conversations");
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          setConversations(data);
        }
      }
    } catch (err) {
      console.error("Failed to fetch conversations:", err);
    }
  }, []);

  // Poll conversation list & WebSocket
  useEffect(() => {
    fetchConversations();
    const interval = setInterval(fetchConversations, 10000); // Polling as fallback

    let ws: WebSocket | null = null;
    let reconnectTimer: NodeJS.Timeout;

    function connectWs() {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = process.env.NEXT_PUBLIC_API_URL 
        ? process.env.NEXT_PUBLIC_API_URL.replace(/^https?:\/\//, "")
        : window.location.host;
      
      // If we're hitting nextjs proxy, it might route /api/v1/operator/ws to backend. 
      // Assuming backend runs on 8000 for local dev if NEXT_PUBLIC_API_URL is missing.
      const wsUrl = process.env.NEXT_PUBLIC_API_URL 
        ? `${protocol}//${host}/api/v1/operator/ws` 
        : `ws://127.0.0.1:8000/api/v1/operator/ws`;
      
      ws = new WebSocket(wsUrl);
      
      ws.onopen = () => setWsConnected(true);
      
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.event === "heartbeat") {
            ws?.send(JSON.stringify({ event: "pong" }));
          } else if (msg.event === "new_escalation") {
            toast.warning(`Новая эскалация от ${msg.data.agent_name}`, {
              description: msg.data.summary,
              duration: 10000,
            });
            // Try to play sound
            try {
              const audio = new Audio('/notification.mp3');
              audio.play().catch(() => {});
            } catch (e) {}
            fetchConversations();
          } else if (msg.event === "conversation_update") {
            fetchConversations();
          }
        } catch (e) {
          // ignore
        }
      };
      
      ws.onclose = () => {
        setWsConnected(false);
        reconnectTimer = setTimeout(connectWs, 3000);
      };
    }

    connectWs();

    return () => {
      clearInterval(interval);
      clearTimeout(reconnectTimer);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, [fetchConversations]);

  // Fetch detailed conversation when selection changes OR periodically
  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }

    let active = true;

    async function loadDetail(showLoading = false) {
      if (showLoading) setIsLoadingDetail(true);
      try {
        const res = await fetch(`/api/conversations/${selectedId}`);
        if (res.ok && active) {
          const data = await res.json();
          setDetail(data);
        }
      } catch (err) {
        console.error("Error loading conversation detail:", err);
      } finally {
        if (showLoading && active) setIsLoadingDetail(false);
      }
    }

    loadDetail(true);

    const interval = setInterval(() => {
      loadDetail(false);
    }, 4000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [selectedId]);

  // Scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [detail?.messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedId || !input.trim() || isSending) return;

    setIsSending(true);
    const result = await sendOperatorMessageAction(selectedId, input);
    setIsSending(false);

    if (result.success) {
      setInput("");
      // Immediate reload
      const res = await fetch(`/api/conversations/${selectedId}`);
      if (res.ok) {
        const data = await res.json();
        setDetail(data);
      }
    } else {
      alert(result.error);
    }
  };

  const handleResolve = async () => {
    if (!selectedId || isResolving) return;
    setIsResolving(true);
    const result = await resolveConversationAction(selectedId);
    setIsResolving(false);
    if (result.success) {
      // Reload detail
      const res = await fetch(`/api/conversations/${selectedId}`);
      if (res.ok) {
        const data = await res.json();
        setDetail(data);
      }
    } else {
      alert(result.error);
    }
  };

  const handleHandoff = async () => {
    if (!selectedId || isHandoff) return;
    setIsHandoff(true);
    const result = await handoffConversationAction(selectedId);
    setIsHandoff(false);
    if (result.success) {
      // Reload detail
      const res = await fetch(`/api/conversations/${selectedId}`);
      if (res.ok) {
        const data = await res.json();
        setDetail(data);
      }
    } else {
      alert(result.error);
    }
  };

  const filteredConversations = conversations.filter((c) => {
    if (filter === "open" && c.status !== "open") return false;
    if (filter === "escalated" && c.status !== "escalated") return false;
    return true;
  });

  return (
    <DashboardShell
      activePath="/operator"
      eyebrow="Консоль"
      title="Рабочее место оператора"
      description="Обработка активных обращений и эскалаций в реальном времени"
    >
      <div className="grid lg:grid-cols-[320px_1fr] gap-6 h-[700px] border border-white/5 bg-zinc-950/20 rounded-2xl overflow-hidden">
        {/* Left pane: Conversation queue */}
        <div className="border-r border-white/5 bg-zinc-900/30 flex flex-col h-full min-w-0">
          <div className="p-4 border-b border-white/5 space-y-3 flex-shrink-0">
            <div className="text-xs font-mono text-zinc-400 uppercase tracking-wider flex items-center justify-between">
              <span>Очередь диалогов ({filteredConversations.length})</span>
              <div title={wsConnected ? "Connected to real-time updates" : "Reconnecting..."}>
                {wsConnected ? (
                  <Wifi className="w-4 h-4 text-emerald-500" />
                ) : (
                  <WifiOff className="w-4 h-4 text-zinc-600 animate-pulse" />
                )}
              </div>
            </div>
            <div className="flex gap-1.5 bg-black/40 p-1 rounded-lg border border-white/5">
              <button
                onClick={() => setFilter("all")}
                className={`flex-1 text-[11px] font-semibold py-1 rounded transition-colors ${
                  filter === "all" ? "bg-white/10 text-white" : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                Все
              </button>
              <button
                onClick={() => setFilter("open")}
                className={`flex-1 text-[11px] font-semibold py-1 rounded transition-colors ${
                  filter === "open" ? "bg-white/10 text-white" : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                Open
              </button>
              <button
                onClick={() => setFilter("escalated")}
                className={`flex-1 text-[11px] font-semibold py-1 rounded transition-colors ${
                  filter === "escalated" ? "bg-white/10 text-white" : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                Escalated
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-white/5">
            {filteredConversations.length === 0 ? (
              <div className="p-8 text-center text-zinc-500 text-xs">
                Нет активных диалогов
              </div>
            ) : (
              filteredConversations.map((c) => {
                const isSelected = c.id === selectedId;
                return (
                  <button
                    key={c.id}
                    onClick={() => setSelectedId(c.id)}
                    className={`w-full text-left p-4 flex flex-col gap-1 transition-colors hover:bg-white/[0.02] ${
                      isSelected ? "bg-white/[0.04] border-l-2 border-purple-500" : ""
                    }`}
                  >
                    <div className="flex justify-between items-center w-full">
                      <span className="text-xs font-mono text-zinc-500">{c.channel}</span>
                      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded uppercase font-semibold ${
                        c.status === "escalated" ? "bg-rose-500/10 text-rose-400" : "bg-amber-500/10 text-amber-400"
                      }`}>
                        {c.status}
                      </span>
                    </div>
                    <span className="text-sm font-semibold text-white truncate w-full">{c.customer}</span>
                    <span className="text-xs text-zinc-400 truncate w-full">{c.summary}</span>
                    <span className="text-[10px] text-zinc-500 text-right w-full">{c.updatedAt}</span>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right pane: Chat Area */}
        <div className="flex flex-col h-full bg-zinc-950/40 relative">
          {isLoadingDetail && (
            <div className="absolute inset-0 bg-black/20 backdrop-blur-[1px] flex items-center justify-center z-10">
              <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
            </div>
          )}

          {detail ? (
            <>
              {/* Header */}
              <div className="p-4 border-b border-white/5 bg-zinc-950/80 flex items-center justify-between flex-shrink-0">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-white truncate">{detail.customer}</span>
                    <span className="text-[10px] text-zinc-500 font-mono">({detail.channel})</span>
                  </div>
                  <p className="text-xs text-zinc-400 truncate mt-0.5">{detail.summary}</p>
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  {detail.status !== "escalated" && detail.status !== "resolved" && (
                    <button
                      onClick={handleHandoff}
                      disabled={isHandoff}
                      className="text-xs px-3 py-1.5 rounded-lg border border-amber-500/20 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 transition-colors font-medium disabled:opacity-50"
                    >
                      Handoff
                    </button>
                  )}
                  {detail.status !== "resolved" && (
                    <button
                      onClick={handleResolve}
                      disabled={isResolving}
                      className="text-xs px-3 py-1.5 rounded-lg border border-emerald-500/20 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition-colors font-medium disabled:opacity-50"
                    >
                      Resolve
                    </button>
                  )}
                </div>
              </div>

              {/* Message Transcript */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {detail.messages.map((message) => {
                  const isCustomer = message.role === "customer";
                  const isOperator = message.role === "operator";
                  return (
                    <div key={message.id} className={`flex gap-3 ${isCustomer ? "" : "flex-row-reverse"}`}>
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                        isCustomer
                          ? "bg-blue-500/10 text-blue-400"
                          : isOperator
                          ? "bg-purple-500/10 text-purple-400"
                          : "bg-emerald-500/10 text-emerald-400"
                      }`}>
                        {isCustomer ? <User className="w-4 h-4" /> : isOperator ? <Headset className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                      </div>
                      <div className={`max-w-[75%] flex flex-col ${isCustomer ? "" : "items-end"}`}>
                        <div className={`rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
                          isCustomer
                            ? "bg-blue-500/10 text-zinc-100 rounded-tl-none"
                            : isOperator
                            ? "bg-purple-500/10 text-zinc-100 rounded-tr-none"
                            : "bg-zinc-800 text-zinc-100 rounded-tr-none"
                        }`}>
                          {message.content}
                        </div>
                        <div className="flex items-center gap-1.5 mt-1 text-[10px] text-zinc-500 font-mono">
                          <span className="capitalize">{message.role}</span>
                          <span>·</span>
                          <span>{message.createdAt}</span>
                        </div>
                        {message.sources && message.sources.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1.5">
                            {message.sources.map((s) => (
                              <span key={s} className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[9px] font-mono">
                                {s}
                              </span>
                            ))}
                            {message.confidence !== undefined && message.confidence !== null && (
                              <span className="px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 text-[9px] font-mono">
                                conf: {(message.confidence * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
                <div ref={bottomRef} />
              </div>

              {/* Chat Input */}
              {detail.status !== "resolved" ? (
                <div className="p-4 border-t border-white/5 bg-zinc-950/80 flex-shrink-0">
                  <form onSubmit={handleSend} className="relative flex items-center">
                    <input
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder="Напишите ответ клиенту..."
                      className="w-full bg-black border border-white/10 rounded-xl pl-4 pr-12 py-3 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all font-sans"
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
              ) : (
                <div className="p-4 border-t border-white/5 bg-zinc-950/80 text-center text-xs text-zinc-500 font-medium uppercase tracking-wider flex-shrink-0">
                  Диалог закрыт. Отправка сообщений заблокирована.
                </div>
              )}
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-zinc-500">
              <MessageSquare className="w-12 h-12 mb-3 text-zinc-700" />
              <p className="text-sm">Выберите диалог в очереди для начала работы</p>
            </div>
          )}
        </div>
      </div>
    </DashboardShell>
  );
}
