"use client";

import { use, useEffect, useRef, useState } from "react";
import { Bot, Send, User } from "lucide-react";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
};

type WidgetChatResponse = {
  conversation_id: string;
  response: string;
  status: "ok";
};

const API_PREFIX = "api/v1";

function trimTrailingSlashes(value: string) {
  return value.replace(/\/+$/, "");
}

function buildWidgetChatUrl(agentId: string) {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!baseUrl) {
    return null;
  }

  const url = new URL(`${trimTrailingSlashes(baseUrl)}/`);
  const basePath = trimTrailingSlashes(url.pathname);
  const requestPath = `widget/chat/${encodeURIComponent(agentId)}`;
  const path = basePath.endsWith(`/${API_PREFIX}`)
    ? requestPath
    : `${API_PREFIX}/${requestPath}`;

  url.pathname = [basePath, path].filter(Boolean).join("/");
  return url.toString();
}

export default function WidgetPage({ params }: { params: Promise<{ agentId: string }> }) {
  const { agentId } = use(params);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Здравствуйте! Я AI-агент CallForce. Чем могу помочь?",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [hasSubmittedInfo, setHasSubmittedInfo] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let sid = localStorage.getItem(`cf_widget_session_${agentId}`);
    if (!sid) {
      sid = crypto.randomUUID();
      localStorage.setItem(`cf_widget_session_${agentId}`, sid);
    }
    setSessionId(sid);

    const savedName = localStorage.getItem(`cf_widget_name_${agentId}`);
    const savedPhone = localStorage.getItem(`cf_widget_phone_${agentId}`);
    if (savedName) setCustomerName(savedName);
    if (savedPhone) setCustomerPhone(savedPhone);
    if (savedName || savedPhone) {
      setHasSubmittedInfo(true);
    }
  }, [agentId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const addAssistantMessage = (content: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: "assistant",
        content,
        timestamp: new Date(),
      },
    ]);
  };

  const handleSend = async (event?: React.FormEvent) => {
    event?.preventDefault();
    const text = inputValue.trim();
    if (!text || !sessionId || isTyping) {
      return;
    }

    const chatUrl = buildWidgetChatUrl(agentId);
    if (!chatUrl) {
      addAssistantMessage("Виджет не настроен: не задан NEXT_PUBLIC_API_URL.");
      return;
    }

    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: text,
        timestamp: new Date(),
      },
    ]);
    setInputValue("");
    setIsTyping(true);

    try {
      const response = await fetch(chatUrl, {
        body: JSON.stringify({
          session_id: sessionId,
          message: text,
          customer_name: customerName || undefined,
          customer_phone: customerPhone || undefined,
        }),
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        method: "POST",
      });

      if (!response.ok) {
        addAssistantMessage("Не удалось получить ответ. Попробуйте ещё раз чуть позже.");
        return;
      }

      const data = (await response.json()) as WidgetChatResponse;
      addAssistantMessage(data.response);
    } catch (error) {
      console.error(error);
      addAssistantMessage("Ошибка сети. Проверьте подключение и попробуйте снова.");
    } finally {
      setIsTyping(false);
    }
  };

  const handleInfoSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (customerName) localStorage.setItem(`cf_widget_name_${agentId}`, customerName);
    if (customerPhone) localStorage.setItem(`cf_widget_phone_${agentId}`, customerPhone);
    setHasSubmittedInfo(true);
  };

  if (!hasSubmittedInfo) {
    return (
      <div className="flex h-screen w-full flex-col bg-zinc-950 font-sans items-center justify-center p-6">
        <div className="w-full max-w-sm bg-zinc-900/50 border border-white/10 rounded-2xl p-6 shadow-xl backdrop-blur-md">
          <div className="flex flex-col items-center mb-6 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500 mb-4">
              <Bot className="h-6 w-6" />
            </div>
            <h2 className="text-lg font-semibold text-white">CallForce AI</h2>
            <p className="text-sm text-zinc-400 mt-1">Оставьте контакты, чтобы мы могли связаться с вами, если вы уйдете.</p>
          </div>
          
          <form onSubmit={handleInfoSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1">Имя (необязательно)</label>
              <input
                type="text"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                placeholder="Как к вам обращаться?"
                className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1">Телефон (необязательно)</label>
              <input
                type="tel"
                value={customerPhone}
                onChange={(e) => setCustomerPhone(e.target.value)}
                placeholder="+7 (999) 000-00-00"
                className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors"
              />
            </div>
            <div className="pt-2">
              <button
                type="submit"
                className="w-full bg-white text-black text-sm font-semibold py-2.5 rounded-lg hover:bg-zinc-200 transition-colors"
              >
                Начать чат
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-zinc-950 font-sans">
      <div className="flex shrink-0 items-center justify-between border-b border-white/10 bg-zinc-900/80 p-4 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-white">CallForce AI</h3>
            <div className="mt-0.5 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
              <span className="text-xs text-zinc-400">Онлайн</span>
            </div>
          </div>
        </div>
      </div>

      <div className="scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent flex flex-1 flex-col space-y-4 overflow-y-auto p-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex w-full gap-2 ${
              message.role === "user" ? "flex-row-reverse" : "flex-row"
            }`}
          >
            <div
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                message.role === "user"
                  ? "bg-white/10 text-zinc-300"
                  : "bg-emerald-500/10 text-emerald-500"
              }`}
            >
              {message.role === "user" ? (
                <User className="h-4 w-4" />
              ) : (
                <Bot className="h-4 w-4" />
              )}
            </div>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-[15px] leading-relaxed ${
                message.role === "user"
                  ? "rounded-tr-sm bg-white text-black"
                  : "rounded-tl-sm border border-white/5 bg-white/5 text-zinc-200"
              }`}
            >
              {message.content}
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex w-full gap-2">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500">
              <Bot className="h-4 w-4" />
            </div>
            <div className="flex h-12 items-center gap-1 rounded-2xl rounded-tl-sm border border-white/5 bg-white/5 px-4 py-4">
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-400" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-400 delay-100" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-400 delay-200" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} className="shrink-0" />
      </div>

      <div className="shrink-0 border-t border-white/10 bg-zinc-950 p-4 pb-6">
        <form
          onSubmit={handleSend}
          className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 py-1.5 pl-4 pr-1.5 transition-colors focus-within:border-white/20 focus-within:bg-white/10"
        >
          <input
            className="h-9 flex-1 bg-transparent text-[15px] text-white outline-none placeholder:text-zinc-500"
            maxLength={4000}
            onChange={(event) => setInputValue(event.target.value)}
            placeholder="Напишите сообщение..."
            type="text"
            value={inputValue}
          />
          <button
            aria-label="Отправить сообщение"
            className="flex h-10 w-10 items-center justify-center rounded-full bg-white text-black transition-colors hover:scale-105 active:scale-95 disabled:bg-white/10 disabled:text-zinc-500 disabled:opacity-50"
            disabled={!inputValue.trim() || !sessionId || isTyping}
            type="submit"
          >
            <Send className="ml-0.5 h-5 w-5" />
          </button>
        </form>
        <div className="mt-3 text-center">
          <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-600">
            Powered by CallForce
          </span>
        </div>
      </div>
    </div>
  );
}
