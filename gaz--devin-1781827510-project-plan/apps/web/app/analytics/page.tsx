import { DashboardShell } from "../components/DashboardShell";
import { BarChart3, TrendingUp, MessageSquare, Bot, AlertTriangle, Zap } from "lucide-react";
import { MiniBarChart, ChannelList } from "./ChartsWrapper";
import { getAnalyticsOverview, UnresolvedTopic } from "../../lib/mvp-data";
import { ResultNotice } from "../components/ResultNotice";

function StatCard({
  label,
  value,
  icon: Icon,
  color = "emerald",
}: {
  label: string;
  value: string | number;
  icon: typeof BarChart3;
  color?: string;
}) {
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
        <div
          className={`w-8 h-8 rounded-lg flex items-center justify-center ${
            colorMap[color] || colorMap.zinc
          }`}
        >
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="text-3xl font-bold text-white tracking-tight">{value}</div>
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
  const result = await getAnalyticsOverview();
  const data = result.data;

  return (
    <DashboardShell
      activePath="/analytics"
      eyebrow="Analytics"
      title="Аналитика"
      description="Метрики, каналы, агенты и нерешённые вопросы"
    >
      <ResultNotice result={result} />

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Всего диалогов" value={data.total_conversations} icon={MessageSquare} color="blue" />
        <StatCard label="Автоматизация" value={`${data.automation_rate}%`} icon={TrendingUp} color="emerald" />
        <StatCard label="Эскалации" value={data.escalated} icon={AlertTriangle} color="amber" />
        <StatCard
          label="Агентов активно"
          value={`${data.active_agents} / ${data.total_agents}`}
          icon={Bot}
          color="purple"
        />
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
    </DashboardShell>
  );
}
