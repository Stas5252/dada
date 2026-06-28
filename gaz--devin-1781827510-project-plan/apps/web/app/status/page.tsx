import Link from "next/link";
import { ArrowLeft, Activity, Wifi, Database, Server, ShieldCheck } from "lucide-react";

interface ServiceStatus {
  name: string;
  status: "operational" | "degraded" | "outage";
  latency?: string;
  uptime?: string;
}

const services: ServiceStatus[] = [
  {
    name: "Core API",
    status: "operational",
    latency: "~45ms",
    uptime: "99.99%",
  },
  {
    name: "WebSocket / Voice",
    status: "operational",
    latency: "~120ms",
    uptime: "99.95%",
  },
  {
    name: "iiko Integration",
    status: "operational",
    latency: "~210ms",
    uptime: "99.8%",
  },
  {
    name: "RAG / Qdrant",
    status: "operational",
    latency: "~85ms",
    uptime: "99.9%",
  },
  {
    name: "YooKassa Payments",
    status: "operational",
    latency: "~150ms",
    uptime: "99.99%",
  },
  {
    name: "Telegram / WhatsApp / VK",
    status: "operational",
    latency: "~60ms",
    uptime: "99.9%",
  },
];

function StatusPill({ status }: { status: ServiceStatus["status"] }) {
  const styles = {
    operational: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    degraded: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    outage: "bg-rose-500/10 text-rose-400 border-rose-500/20",
  };

  const labels = {
    operational: "Работает",
    degraded: "Замедление",
    outage: "Остановка",
  };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${styles[status]}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {labels[status]}
    </span>
  );
}

export const metadata = {
  title: "Статус системы — CallForce",
};

export default function StatusPage() {
  const allOperational = services.every((s) => s.status === "operational");

  return (
    <main className="min-h-screen bg-black text-white">
      <header className="border-b border-white/5 bg-zinc-950/80">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-6">
          <Link href="/" className="flex items-center gap-2 text-sm font-medium text-zinc-400 transition-colors hover:text-white">
            <ArrowLeft className="h-4 w-4" />
            На главную
          </Link>
          <span className="text-xs font-mono text-zinc-500">status.callforce.ru</span>
        </div>
      </header>

      <section className="mx-auto max-w-5xl px-6 py-16">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6 mb-12">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10 text-white">
                <Activity className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-emerald-400">Система</p>
                <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Статус всех сервисов</h1>
              </div>
            </div>
            <p className="text-zinc-400 mt-2">
              {allOperational
                ? "Все сервисы работают штатно. Последнее обновление: только что."
                : "Есть проблемы с отдельными сервисами. Команда уже работает над восстановлением."}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {allOperational ? (
              <StatusPill status="operational" />
            ) : (
              <StatusPill status="degraded" />
            )}
          </div>
        </div>

        <div className="space-y-4">
          {services.map((service) => (
            <div key={service.name} className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl border border-white/5 bg-zinc-900/30 hover:border-white/10 transition-colors">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-zinc-800 flex items-center justify-center border border-white/5 shrink-0">
                  {service.name.includes("API") && <Server className="h-5 w-5 text-zinc-100" />}
                  {service.name.includes("WebSocket") && <Wifi className="h-5 w-5 text-zinc-100" />}
                  {service.name.includes("RAG") && <Database className="h-5 w-5 text-zinc-100" />}
                  {service.name.includes("YooKassa") && <ShieldCheck className="h-5 w-5 text-zinc-100" />}
                  {service.name.includes("Telegram") && <Activity className="h-5 w-5 text-zinc-100" />}
                  {service.name.includes("iiko") && <Database className="h-5 w-5 text-zinc-100" />}
                </div>
                <div>
                  <h3 className="text-white font-semibold">{service.name}</h3>
                  <p className="text-xs text-zinc-500 mt-0.5">Uptime: {service.uptime}</p>
                </div>
              </div>
              <div className="flex items-center gap-6 md:gap-8">
                {service.latency && (
                  <span className="text-sm font-mono text-zinc-400">Latency {service.latency}</span>
                )}
                <StatusPill status={service.status} />
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12 p-6 rounded-2xl border border-white/5 bg-zinc-900/30">
          <h2 className="text-lg font-semibold text-white mb-3">История инцидентов</h2>
          <div className="space-y-3 text-sm text-zinc-400">
            <div className="flex items-center justify-between py-2 border-b border-white/5">
              <span>Запланированное техническое обслуживание iiko API</span>
              <span className="text-xs text-zinc-500">15 июня 2026, 02:00 — 04:00 MSK</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span>Восстановление после DDoS на edge (завершено)</span>
              <span className="text-xs text-zinc-500">10 июня 2026, 18:32 MSK</span>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-white/5 py-8 bg-black">
        <div className="mx-auto max-w-5xl px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <span className="text-xs text-zinc-600">© 2026 CallForce Inc.</span>
          <Link href="/docs" className="text-sm text-zinc-500 hover:text-white transition-colors">Документация</Link>
        </div>
      </footer>
    </main>
  );
}
