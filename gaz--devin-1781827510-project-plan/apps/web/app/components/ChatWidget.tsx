"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, MessageSquare, Send, User, X } from "lucide-react";

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

export function ChatWidget() {
  const agentId = process.env.NEXT_PUBLIC_WIDGET_AGENT_ID?.trim() ?? "";
  const [isOpen, setIsOpen] = useState(false);
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
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!agentId) {
      return;
    }

    let sid = localStorage.getItem(`cf_widget_session_${agentId}`);
    if (!sid) {
      sid = crypto.randomUUID();
      localStorage.setItem(`cf_widget_session_${agentId}`, sid);
    }
    setSessionId(sid);
  }, [agentId]);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isTyping, isOpen]);

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
    if (!text || isTyping) {
      return;
    }

    if (!agentId) {
      addAssistantMessage("Чат не настроен: укажите NEXT_PUBLIC_WIDGET_AGENT_ID.");
      return;
    }

    const chatUrl = buildWidgetChatUrl(agentId);
    if (!chatUrl || !sessionId) {
      addAssistantMessage("Чат не настроен: проверьте NEXT_PUBLIC_API_URL.");
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

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
      <div
        className={`mb-4 origin-bottom-right overflow-hidden rounded-2xl border border-white/10 bg-zinc-950 shadow-2xl transition-all duration-300 ${
          isOpen
            ? "translate-y-0 scale-100 opacity-100"
            : "pointer-events-none translate-y-4 scale-95 opacity-0"
        }`}
        style={{ width: "350px", height: "500px" }}
      >
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between border-b border-white/10 bg-zinc-900/50 p-4 backdrop-blur-md">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500">
                <Bot className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-medium text-white">CallForce AI</h3>
                <div className="flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
                  <span className="text-xs text-zinc-400">Онлайн</span>
                </div>
              </div>
            </div>
            <button
              aria-label="Закрыть чат"
              className="text-zinc-400 transition-colors hover:text-white"
              onClick={() => setIsOpen(false)}
              type="button"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent flex-1 space-y-4 overflow-y-auto p-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-2 ${
                  message.role === "user" ? "flex-row-reverse" : "flex-row"
                }`}
              >
                <div
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
                    message.role === "user"
                      ? "bg-white/10 text-zinc-300"
                      : "bg-emerald-500/10 text-emerald-500"
                  }`}
                >
                  {message.role === "user" ? (
                    <User className="h-3 w-3" />
                  ) : (
                    <Bot className="h-3 w-3" />
                  )}
                </div>
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm leading-relaxed ${
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
              <div className="flex gap-2">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500">
                  <Bot className="h-3 w-3" />
                </div>
                <div className="flex items-center gap-1 rounded-2xl rounded-tl-sm border border-white/5 bg-white/5 px-4 py-3">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-400" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-400 delay-100" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-400 delay-200" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="border-t border-white/10 bg-zinc-950 p-4">
            <form
              className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 py-1.5 pl-4 pr-1.5 transition-colors focus-within:border-white/20 focus-within:bg-white/10"
              onSubmit={handleSend}
            >
              <input
                className="flex-1 bg-transparent text-sm text-white outline-none placeholder:text-zinc-500"
                maxLength={4000}
                onChange={(event) => setInputValue(event.target.value)}
                placeholder="Напишите сообщение..."
                type="text"
                value={inputValue}
              />
              <button
                aria-label="Отправить сообщение"
                className="flex h-8 w-8 items-center justify-center rounded-full bg-white text-black transition-colors disabled:bg-white/10 disabled:text-zinc-500 disabled:opacity-50"
                disabled={!inputValue.trim() || isTyping}
                type="submit"
              >
                <Send className="h-4 w-4" />
              </button>
            </form>
            <div className="mt-2 text-center">
              <span className="text-[10px] font-medium uppercase tracking-wide text-zinc-600">
                Powered by CallForce
              </span>
            </div>
          </div>
        </div>
      </div>

      <button
        aria-label={isOpen ? "Закрыть чат" : "Открыть чат"}
        className="group relative flex h-14 w-14 items-center justify-center rounded-full bg-white text-black shadow-lg transition-all hover:scale-105 active:scale-95"
        onClick={() => setIsOpen(!isOpen)}
        type="button"
      >
        <div className="absolute inset-0 rounded-full bg-white opacity-20 group-hover:animate-ping" />
        {isOpen ? <X className="h-6 w-6" /> : <MessageSquare className="h-6 w-6" />}
      </button>
    </div>
  );
}
