"use client";

import { useState } from "react";
import Link from "next/link";
import { MessageSquare, Phone, AlertTriangle, CheckCircle, Search } from "lucide-react";
import { StatusPill } from "./StatusPill";
import { EmptyState } from "./EmptyState";
import type { ConversationSummary } from "../../lib/mvp-data";

function conversationTone(status: "draft" | "escalated" | "open" | "resolved") {
  if (status === "resolved") {
    return "ok";
  }
  if (status === "escalated") {
    return "danger";
  }
  return "warn";
}

type ConversationsListProps = {
  initialConversations: ConversationSummary[];
};

type FilterType = "all" | "telegram" | "sip" | "escalated" | "resolved";

export function ConversationsList({ initialConversations }: ConversationsListProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<FilterType>("all");

  const filteredConversations = initialConversations.filter((c) => {
    // Filter by channel/status
    if (activeFilter === "telegram" && c.channel !== "Telegram") return false;
    if (activeFilter === "sip" && c.channel !== "SIP") return false;
    if (activeFilter === "escalated" && c.status !== "escalated") return false;
    if (activeFilter === "resolved" && c.status !== "resolved") return false;

    // Filter by search
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      const matchCustomer = c.customer.toLowerCase().includes(query);
      const matchSummary = c.summary.toLowerCase().includes(query);
      const matchId = c.id.toLowerCase().includes(query);
      return matchCustomer || matchSummary || matchId;
    }

    return true;
  });

  return (
    <div className="space-y-6">
      {/* Search & Filter Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input
            type="text"
            placeholder="Поиск по клиенту или содержанию..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-black/40 border border-white/10 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors"
          />
        </div>

        {/* Filter buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => setActiveFilter("all")}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-colors border ${
              activeFilter === "all"
                ? "bg-white text-black border-white"
                : "bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white border-white/5"
            }`}
          >
            Все
          </button>
          <button
            type="button"
            onClick={() => setActiveFilter("telegram")}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-colors border ${
              activeFilter === "telegram"
                ? "bg-white text-black border-white"
                : "bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white border-white/5"
            }`}
          >
            <span className="inline-flex items-center gap-1.5">
              <MessageSquare className="w-3 h-3" />
              Telegram
            </span>
          </button>
          <button
            type="button"
            onClick={() => setActiveFilter("sip")}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-colors border ${
              activeFilter === "sip"
                ? "bg-white text-black border-white"
                : "bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white border-white/5"
            }`}
          >
            <span className="inline-flex items-center gap-1.5">
              <Phone className="w-3 h-3" />
              SIP
            </span>
          </button>
          <button
            type="button"
            onClick={() => setActiveFilter("escalated")}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-colors border ${
              activeFilter === "escalated"
                ? "bg-white text-black border-white"
                : "bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white border-white/5"
            }`}
          >
            <span className="inline-flex items-center gap-1.5">
              <AlertTriangle className="w-3 h-3" />
              Escalated
            </span>
          </button>
          <button
            type="button"
            onClick={() => setActiveFilter("resolved")}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-colors border ${
              activeFilter === "resolved"
                ? "bg-white text-black border-white"
                : "bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white border-white/5"
            }`}
          >
            <span className="inline-flex items-center gap-1.5">
              <CheckCircle className="w-3 h-3" />
              Resolved
            </span>
          </button>
        </div>
      </div>

      {/* Table */}
      <section className="bg-zinc-900/50 border border-white/5 rounded-xl overflow-hidden">
        {filteredConversations.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/5 bg-zinc-950/50">
                  <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Клиент</th>
                  <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Канал</th>
                  <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Статус</th>
                  <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Summary</th>
                  <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Latency</th>
                  <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Обновлен</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredConversations.map((conversation) => (
                  <tr key={conversation.id} className="hover:bg-white/[0.04] transition-colors group cursor-pointer">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-300 font-medium">
                      <Link
                        href={`/conversations/${conversation.id}`}
                        className="hover:text-white hover:underline decoration-white/20 underline-offset-4 transition-colors"
                      >
                        {conversation.customer}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-400">
                      {conversation.channel}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusPill tone={conversationTone(conversation.status)}>{conversation.status}</StatusPill>
                    </td>
                    <td className="px-6 py-4 text-sm text-zinc-300 max-w-xs truncate">
                      {conversation.summary}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-zinc-400">
                      {conversation.latency}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-500">
                      {conversation.updatedAt}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            description="Ничего не найдено. Попробуйте изменить параметры поиска или фильтр."
            title="Нет подходящих диалогов"
          />
        )}
      </section>
    </div>
  );
}
