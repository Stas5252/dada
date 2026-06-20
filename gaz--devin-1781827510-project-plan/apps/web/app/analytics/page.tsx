import { DashboardShell } from "../components/DashboardShell";
import { fetchCoreApi } from "../../lib/core-api";
import { BarChart3, TrendingUp, MessageSquare, Bot, AlertTriangle, Zap } from "lucide-react";

type ChannelBreakdown = { channel: string; count: number };
type DailyConversation = { date: string; count: number };
type UnresolvedTopic = { question: string; count: number; last_seen: string };

type AnalyticsOverview = {
  total_conversations: number;
  resolved: number;
  escalated: number;
  open: number;
  automation_rate: number;
  total_agents: number;
  active_agents: number;
  total_knowledge_sources: number;
  total_messages: number;
  avg_messages_per_conversation: number;
  conversations_by_channel: ChannelBreakdown[];
  conversations_by_day: DailyConversation[];
  top_unresolved: UnresolvedTopic[];
};

async function getAnalytics(): Promise<AnalyticsOverview | null> {
  const result = await fetchCoreApi<AnalyticsOverview>("/api/v1/analytics/overview");
  if (result.state === "live") return result.data;
  return null;
}

function StatCard({ label, value, icon: Icon, color = "emerald" }: { label: string; value: string | number; icon: typeof BarChart3; color?: string }) {
  const colorMap: Record<string, string> = {
    emerald: "text-emerald-500 bg-emerald-500/10",
    blue: "text-blue-500 bg-blue-500/10",
    amber: "text-amber-500 bg-amber-500/10",
    red: "text-red-500 bg-red-500/10",
    purple: "text-purple-500 bg-purple-500/10",
    zinc: "text-zinc-400 bg-zinc-500/10",
  };
  return (
    <div className="p-6 rounded-2xl border border-white/5 bg-zinc-900/50">
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-medium text-zinc-400">{label}</span>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${colorMap[color] || colorMap.zinc}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="text-3xl font-bold text-white tracking-tight">{value}</div>
    </div>
  );
}

function MiniBarChart({ data }: { data: DailyConversation[] }) {
  const maxCount = Math.max(...data.map(d => d.count), 1);
  // Show last 14 days for compact view
  const recent = data.slice(-14);

  return (
    <div className="p-6 rounded-2xl border border-white/5 bg-zinc-900/50">
      <h3 className="text-sm font-medium text-zinc-400 mb-4">Диалоги за последние 14 дней</h3>
      <div className="flex items-end gap-1 h-32">
        {recent.map((day, i) => (
          <div key={day.date} className="flex-1 flex flex-col items-center gap-1">
            <div
              className="w-full rounded-t bg-emerald-500/80 hover:bg-emerald-500 transition-colors min-h-[2px]"
              style={{ height: `${Math.max((day.count / maxCount) * 100, 2)}%` }}
              title={`${day.date}: ${day.count} диалогов`}
            />
            {i % 2 === 0 && (
              <span className="text-[9px] text-zinc-600 tabular-nums">
                {day.date.slice(5)}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function ChannelList({ channels }: { channels: ChannelBreakdown[] }) {
  const channelNames: Record<string, string> = {
    telegram: "Telegram",
    web_widget: "Web Widget",
    whatsapp: "WhatsApp",
    vk: "VK",
    sip: "SIP / Телефон",
    voice: "Голос",
  };
  const total = channels.reduce((sum, c) => sum + c.count, 0) || 1;

  return (
    <div className="p-6 rounded-2xl border border-white/5 bg-zinc-900/50">
      <h3 className="text-sm font-medium text-zinc-400 mb-4">Каналы</h3>
      <div className="space-y-3">
        {channels.length === 0 && <p className="text-sm text-zinc-500">Нет данных</p>}
        {channels.map((ch) => (
          <div key={ch.channel}>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-zinc-300">{channelNames[ch.channel] || ch.channel}</span>
              <span className="text-zinc-400 tabular-nums">{ch.count}</span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-white/5">
              <div
                className="h-full rounded-full bg-blue-500"
                style={{ width: `${(ch.count / total) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function UnresolvedList({ topics }: { topics: UnresolvedTopic[] }) {
  return (
    <div className="p-6 rounded-2xl border border-white/5 bg-zinc-900/50">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="w-4 h-4 text-amber-500" />
        <h3 className="text-sm font-medium text-zinc-400">Нерешённые вопросы</h3>
      </div>
      {topics.length === 0 ? (
        <p className="text-sm text-zinc-500">Все вопросы решены 🎉</p>
      ) : (
        <div className="space-y-3">
          {topics.map((topic, i) => (
            <div key={i} className="flex items-start gap-3 text-sm">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-500/10 text-amber-500 flex items-center justify-center text-xs font-bold">
                {topic.count}
              </span>
              <span className="text-zinc-300 leading-snug">{topic.question}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default async function AnalyticsPage() {
  const analytics = await getAnalytics();

  // Fallback mock data when API is not available
  const data: AnalyticsOverview = analytics || {
    total_conversations: 42,
    resolved: 36,
    escalated: 4,
    open: 2,
    automation_rate: 85.7,
    total_agents: 3,
    active_agents: 2,
    total_knowledge_sources: 5,
    total_messages: 128,
    avg_messages_per_conversation: 3.0,
    conversations_by_channel: [
      { channel: "telegram", count: 25 },
      { channel: "web_widget", count: 12 },
      { channel: "voice", count: 5 },
    ],
    conversations_by_day: Array.from({ length: 30 }, (_, i) => ({
      date: new Date(Date.now() - (29 - i) * 86400000).toISOString().slice(0, 10),
      count: Math.floor(Math.random() * 5),
    })),
    top_unresolved: [
      { question: "Как вернуть товар по гарантии?", count: 3, last_seen: new Date().toISOString() },
      { question: "Есть ли доставка в регионы?", count: 2, last_seen: new Date().toISOString() },
    ],
  };

  return (
    <DashboardShell
      activePath="/analytics"
      eyebrow="Analytics"
      title="Аналитика"
      description="Метрики, каналы, агенты и нерешённые вопросы"
    >
      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Всего диалогов" value={data.total_conversations} icon={MessageSquare} color="blue" />
        <StatCard label="Автоматизация" value={`${data.automation_rate}%`} icon={TrendingUp} color="emerald" />
        <StatCard label="Эскалации" value={data.escalated} icon={AlertTriangle} color="amber" />
        <StatCard label="Агентов активно" value={`${data.active_agents} / ${data.total_agents}`} icon={Bot} color="purple" />
      </div>

      {/* Charts Row */}
      <div className="grid lg:grid-cols-2 gap-4 mb-8">
        <MiniBarChart data={data.conversations_by_day} />
        <ChannelList channels={data.conversations_by_channel} />
      </div>

      {/* Bottom Row */}
      <div className="grid lg:grid-cols-2 gap-4">
        <UnresolvedList topics={data.top_unresolved} />

        {/* Agent Performance Summary */}
        <div className="p-6 rounded-2xl border border-white/5 bg-zinc-900/50">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-4 h-4 text-purple-500" />
            <h3 className="text-sm font-medium text-zinc-400">Сводка</h3>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-zinc-400">Решённых</span>
              <span className="text-emerald-400 font-medium">{data.resolved}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-zinc-400">Открытых</span>
              <span className="text-blue-400 font-medium">{data.open}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-zinc-400">Всего сообщений</span>
              <span className="text-white font-medium">{data.total_messages}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-zinc-400">Сообщ./диалог (ср.)</span>
              <span className="text-white font-medium">{data.avg_messages_per_conversation}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-zinc-400">Источников знаний</span>
              <span className="text-white font-medium">{data.total_knowledge_sources}</span>
            </div>
          </div>
        </div>
      </div>

      {!analytics && (
        <p className="text-xs text-zinc-600 mt-6 text-center">
          Показаны demo-данные. Подключите API для реальных метрик.
        </p>
      )}
    </DashboardShell>
  );
}
