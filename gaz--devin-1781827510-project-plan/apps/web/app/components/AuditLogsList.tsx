"use client";

import { useState } from "react";
import { ClipboardList, Search, Download, Cpu, Key, User, CreditCard } from "lucide-react";
import { EmptyState } from "./EmptyState";
import type { CoreAuditLog } from "../../lib/core-api";

function formatDateTime(value?: string) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function getEventIcon(eventType: string) {
  if (eventType.includes("login") || eventType.includes("user") || eventType.includes("mfa") || eventType.includes("invite")) {
    return <User className="w-3.5 h-3.5 text-blue-400" />;
  }
  if (eventType.includes("key")) {
    return <Key className="w-3.5 h-3.5 text-amber-400" />;
  }
  if (eventType.includes("billing") || eventType.includes("payment")) {
    return <CreditCard className="w-3.5 h-3.5 text-emerald-400" />;
  }
  return <Cpu className="w-3.5 h-3.5 text-zinc-400" />;
}

type AuditLogsListProps = {
  initialLogs: CoreAuditLog[];
};

type FilterType = "all" | "auth" | "agent" | "keys" | "billing";

export function AuditLogsList({ initialLogs }: AuditLogsListProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<FilterType>("all");

  const filteredLogs = initialLogs.filter((log) => {
    // Filter by type
    if (activeFilter === "auth" && !(log.event_type.includes("login") || log.event_type.includes("user") || log.event_type.includes("mfa") || log.event_type.includes("invite") || log.event_type.includes("team"))) return false;
    if (activeFilter === "agent" && !log.event_type.includes("agent") && !log.event_type.includes("pathway") && !log.event_type.includes("knowledge")) return false;
    if (activeFilter === "keys" && !log.event_type.includes("key")) return false;
    if (activeFilter === "billing" && !log.event_type.includes("billing") && !log.event_type.includes("payment")) return false;

    // Filter by search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchType = log.event_type.toLowerCase().includes(q);
      const matchIp = (log.ip_address || "").toLowerCase().includes(q);
      const matchDetails = Object.values(log.details).some((val) =>
        (val || "").toLowerCase().includes(q)
      );
      return matchType || matchIp || matchDetails;
    }

    return true;
  });

  const exportToCSV = () => {
    const headers = ["ID", "Time", "Event Type", "IP Address", "Details"];
    const rows = filteredLogs.map((log) => [
      log.id,
      log.created_at,
      log.event_type,
      log.ip_address || "",
      JSON.stringify(log.details).replace(/"/g, '""'),
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((r) => r.map((field) => `"${field}"`).join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `audit_logs_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Search & Filter Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input
            type="text"
            placeholder="Поиск по событию, IP-адресу или деталям..."
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
            onClick={() => setActiveFilter("auth")}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-colors border ${
              activeFilter === "auth"
                ? "bg-white text-black border-white"
                : "bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white border-white/5"
            }`}
          >
            Доступ и Команда
          </button>
          <button
            type="button"
            onClick={() => setActiveFilter("agent")}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-colors border ${
              activeFilter === "agent"
                ? "bg-white text-black border-white"
                : "bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white border-white/5"
            }`}
          >
            Агенты и Знания
          </button>
          <button
            type="button"
            onClick={() => setActiveFilter("keys")}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-colors border ${
              activeFilter === "keys"
                ? "bg-white text-black border-white"
                : "bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white border-white/5"
            }`}
          >
            API Ключи
          </button>
          <button
            type="button"
            onClick={() => setActiveFilter("billing")}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-colors border ${
              activeFilter === "billing"
                ? "bg-white text-black border-white"
                : "bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white border-white/5"
            }`}
          >
            Биллинг
          </button>
        </div>
      </div>

      {/* Table Section */}
      <section className="bg-zinc-900/50 border border-white/5 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ClipboardList className="w-4 h-4 text-zinc-400" />
            <span className="text-sm font-medium text-zinc-300">Логи аудита ({filteredLogs.length})</span>
          </div>
          {filteredLogs.length > 0 && (
            <button
              onClick={exportToCSV}
              className="inline-flex items-center gap-1.5 text-xs text-zinc-300 hover:text-white transition-colors bg-white/5 hover:bg-white/10 px-3 py-1.5 rounded-lg border border-white/10 font-medium"
            >
              <Download className="w-3.5 h-3.5" />
              Экспортировать в CSV
            </button>
          )}
        </div>

        {filteredLogs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/5 bg-zinc-950/50">
                  <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Время</th>
                  <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Событие</th>
                  <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">IP-адрес</th>
                  <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Детализация изменений</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-xs font-mono text-zinc-300">
                      {formatDateTime(log.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-white/5 text-zinc-200 border border-white/5">
                        {getEventIcon(log.event_type)}
                        {log.event_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-xs font-mono text-zinc-400">
                      {log.ip_address || "—"}
                    </td>
                    <td className="px-6 py-4 text-xs">
                      <div className="max-w-md space-y-1">
                        {Object.entries(log.details).map(([key, val]) => (
                          <div key={key} className="text-zinc-400">
                            <span className="font-semibold text-zinc-500 font-mono">{key}:</span>{" "}
                            <span className="text-zinc-300">{String(val)}</span>
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            description="Записей не обнаружено. Попробуйте сбросить фильтры или изменить поисковый запрос."
            title="Журнал пуст"
          />
        )}
      </section>
    </div>
  );
}
