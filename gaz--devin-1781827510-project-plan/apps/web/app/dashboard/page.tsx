import Link from "next/link";
import { DashboardShell } from "../components/DashboardShell";
import { ResultNotice } from "../components/ResultNotice";
import { StatusPill } from "../components/StatusPill";
import { ActionNotice } from "../components/ActionNotice";
import { triggerOutboundCallAction } from "../actions";
import { Activity, AlertTriangle, CheckCircle2, ChevronRight, Server, Zap, Phone } from "lucide-react";
import {
  getConversations,
  getDashboardOverview,
  getOnboardingItems,
  getProductionReadiness,
  getAgents,
} from "../../lib/mvp-data";

function alertToneToStatus(tone: "ok" | "warn" | "danger") {
  if (tone === "ok") return "Ready";
  if (tone === "danger") return "Blocked";
  return "Needs attention";
}

type DashboardPageProps = {
  searchParams?: Promise<{
    notice?: string;
  }>;
};

export default async function DashboardPage({ searchParams }: DashboardPageProps) {
  const resolvedSearchParams = await searchParams;
  const notice = resolvedSearchParams?.notice;

  const [overviewResult, conversationsResult, readinessResult, agentsResult] = await Promise.all([
    getDashboardOverview(),
    getConversations(),
    getProductionReadiness(),
    getAgents(),
  ]);
  const onboardingItems = await getOnboardingItems();
  const latestConversations = conversationsResult.data.slice(0, 3);

  return (
    <DashboardShell
      activePath="/dashboard"
      eyebrow="Обзор Пространства"
      title="Панель Управления"
      description="Метрики, статус платформы и следующие шаги для запуска ИИ-агентов."
      actions={
        <Link
          href="/onboarding"
          className="flex items-center gap-2 bg-white text-black px-4 py-2 rounded-lg text-sm font-medium hover:bg-zinc-200 transition-colors"
        >
          <CheckCircle2 className="w-4 h-4" />
          Открыть чеклист
        </Link>
      }
    >
      <div className="space-y-6">
        <ActionNotice notice={notice} />
        <ResultNotice result={overviewResult} />
        <ResultNotice result={conversationsResult} />
        <ResultNotice result={readinessResult} />

        {/* KPIs */}
        <section className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {overviewResult.data.kpis.map((kpi, idx) => (
            <div key={idx} className="glass-panel premium-border p-6 relative overflow-hidden group hover:-translate-y-1 hover:shadow-[0_8px_32px_rgba(168,85,247,0.2)] transition-all duration-300">
              <div className="absolute top-0 right-0 p-4 opacity-10 text-primary group-hover:opacity-30 group-hover:scale-110 group-hover:rotate-12 transition-all duration-500">
                {idx === 0 ? <Activity className="w-12 h-12" /> : idx === 1 ? <Zap className="w-12 h-12" /> : <Server className="w-12 h-12" />}
              </div>
              <div className="text-3xl font-bold text-foreground mb-1 tracking-tight">{kpi.value}</div>
              <div className="text-sm font-medium text-muted-foreground mb-1">{kpi.label}</div>
              <div className="text-xs text-zinc-500">{kpi.detail}</div>
            </div>
          ))}
        </section>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Column */}
          <div className="lg:col-span-2 space-y-6">

            {/* Recent Conversations */}
            <section className="glass-panel premium-border overflow-hidden">
              <div className="p-6 border-b border-border flex items-center justify-between bg-card/40">
                <div>
                  <h2 className="text-lg font-semibold text-foreground">Последние диалоги</h2>
                  <p className="text-sm text-zinc-400">История запросов к агенту.</p>
                </div>
                <Link href="/conversations" className="text-sm text-zinc-400 hover:text-white flex items-center gap-1 transition-colors">
                  Все диалоги <ChevronRight className="w-4 h-4" />
                </Link>
              </div>

              {latestConversations.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-white/5 bg-zinc-950/50">
                        <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Канал</th>
                        <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Статус</th>
                        <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Summary</th>
                        <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Latency</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {latestConversations.map((conversation) => (
                        <tr key={conversation.id} className="hover:bg-white/[0.04] transition-colors">
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-300">
                            {conversation.channel}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <StatusPill tone={conversation.status === "resolved" ? "ok" : "warn"}>
                              {conversation.status}
                            </StatusPill>
                          </td>
                          <td className="px-6 py-4 text-sm text-zinc-300 max-w-xs truncate">
                            <Link href={`/conversations/${conversation.id}`} className="hover:text-white hover:underline decoration-white/20 underline-offset-4 transition-colors">
                              {conversation.summary}
                            </Link>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-zinc-400">
                            {conversation.latency}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-8 text-center text-zinc-500 text-sm">
                  Диалогов пока нет.
                </div>
              )}
            </section>

            {/* Production Readiness */}
            <section className="glass-panel premium-border overflow-hidden">
              <div className="p-6 border-b border-border flex items-center justify-between bg-card/40">
                <div>
                  <h2 className="text-lg font-semibold text-foreground">Статус Интеграций</h2>
                  <p className="text-sm text-zinc-400">
                    Backend runtime: {readinessResult.data.environment} / {readinessResult.data.storeBackend}
                  </p>
                </div>
                <StatusPill tone={readinessResult.data.status === "ready" ? "ok" : "warn"}>
                  {readinessResult.data.status}
                </StatusPill>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-white/5 bg-zinc-950/50">
                      <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Провайдер</th>
                      <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Статус</th>
                      <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Детали</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {readinessResult.data.providers.map((provider) => (
                      <tr key={provider.name} className="hover:bg-white/[0.02] transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-300 font-medium">
                          {provider.name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <StatusPill tone={provider.status === "configured" ? "ok" : "warn"}>
                            {provider.status}
                          </StatusPill>
                        </td>
                        <td className="px-6 py-4 text-sm text-zinc-400">
                          {provider.detail}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>

          {/* Sidebar Column */}
          <div className="space-y-6">

            {/* Outbound Test Call Form */}
            <section className="glass-panel premium-border p-6 relative overflow-hidden">
              <div className="absolute top-0 right-0 p-8 opacity-5 text-primary pointer-events-none">
                <Phone className="w-24 h-24 rotate-12" />
              </div>
              <div className="mb-4 relative z-10">
                <h2 className="text-lg font-semibold text-foreground">Тест исходящего звонка</h2>
                <p className="text-sm text-zinc-400">Робот совершит звонок на указанный номер телефона.</p>
              </div>

              {agentsResult.data && agentsResult.data.length > 0 ? (
                <form action={triggerOutboundCallAction} className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-zinc-400 block">Агент для звонка</label>
                    <select
                      name="agent_id"
                      className="w-full bg-black border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500 transition-colors"
                      required
                    >
                      {agentsResult.data.map((agent) => (
                        <option key={agent.id} value={agent.id}>
                          {agent.name} ({agent.channel === "sip" ? "SIP Voice" : agent.channel})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-zinc-400 block">Номер телефона (E.164)</label>
                    <input
                      type="tel"
                      name="to_number"
                      placeholder="+79991234567"
                      className="w-full bg-black border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500 transition-colors"
                      required
                    />
                  </div>

                  <button
                    type="submit"
                    className="w-full bg-white text-black text-xs font-bold py-2.5 rounded-lg hover:bg-zinc-200 transition-colors flex items-center justify-center gap-2"
                  >
                    <Phone className="w-3.5 h-3.5" />
                    Запустить звонок
                  </button>
                </form>
              ) : (
                <div className="text-xs text-zinc-500 bg-zinc-950 p-4 rounded-lg border border-white/5 text-center">
                  Сначала создайте агента с поддержкой звонков (SIP) в конструкторе.
                </div>
              )}
            </section>

            {/* Alerts */}
            <section className="glass-panel premium-border p-6">
              <div className="mb-4">
                <h2 className="text-lg font-semibold text-foreground">Уведомления</h2>
                <p className="text-sm text-zinc-400">Сигналы системы.</p>
              </div>
              <div className="space-y-4">
                {overviewResult.data.alerts.map((alert) => (
                  <div key={alert.title} className="flex gap-4 p-4 rounded-lg border border-white/5 bg-zinc-950">
                    <div className="flex-shrink-0 mt-1">
                      <AlertTriangle className={`w-5 h-5 ${alert.tone === 'danger' ? 'text-red-500' : alert.tone === 'warn' ? 'text-amber-500' : 'text-emerald-500'}`} />
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-white mb-1">{alert.title}</h3>
                      <p className="text-sm text-zinc-400 mb-3">{alert.description}</p>
                      <StatusPill tone={alert.tone}>{alertToneToStatus(alert.tone)}</StatusPill>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Onboarding */}
            <section className="glass-panel premium-border p-6">
              <div className="mb-4">
                <h2 className="text-lg font-semibold text-foreground">Чеклист запуска</h2>
                <p className="text-sm text-zinc-400">Следующие шаги.</p>
              </div>
              <div className="space-y-2">
                {onboardingItems.map((item) => (
                  <Link
                    key={item.id}
                    href={item.href}
                    className="flex items-center gap-3 p-3 rounded-lg hover:bg-white/5 hover:translate-x-1 transition-all duration-300 group"
                  >
                    <div className={`w-2 h-2 rounded-full flex-shrink-0 ${item.status === 'done' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : item.status === 'current' ? 'bg-amber-500 animate-pulse' : 'bg-zinc-700'}`} />
                    <span className={`text-sm ${item.status === 'done' ? 'text-zinc-500 line-through' : item.status === 'current' ? 'text-white font-medium' : 'text-zinc-400'} group-hover:text-white transition-colors`}>
                      {item.title}
                    </span>
                  </Link>
                ))}
              </div>
            </section>

          </div>
        </div>
      </div>
    </DashboardShell>
  );
}
