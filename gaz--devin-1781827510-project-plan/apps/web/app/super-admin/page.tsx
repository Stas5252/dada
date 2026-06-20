import { DashboardShell } from "../components/DashboardShell";
import { StatusPill } from "../components/StatusPill";
import { Activity, Users, ShieldAlert, Database } from "lucide-react";

export const metadata = {
  title: "Super Admin — CallForce",
};

export default function SuperAdminPage() {
  // Mock data for the admin panel
  const tenants = [
    { id: "00000000-0000-0000-0000-000000000001", name: "Demo Restaurant", status: "active", mrr: "$120", agents: 2, convs: 128 },
    { id: "98765432-1234-5678-1234-567812345678", name: "Alpha Logistics", status: "trialing", mrr: "$0", agents: 1, convs: 45 },
    { id: "11111111-2222-3333-4444-555555555555", name: "Beta Medical", status: "suspended", mrr: "$45", agents: 3, convs: 12 },
  ];

  return (
    <DashboardShell
      activePath="/super-admin"
      eyebrow="Управление Платформой"
      title="Super Admin Panel"
      description="Глобальные метрики и управление всеми клиентами (Tenants)."
    >
      <div className="space-y-6">

        {/* KPIs */}
        <section className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-zinc-900/50 border border-white/5 rounded-xl p-6">
            <div className="text-zinc-500 mb-2"><Users className="w-5 h-5" /></div>
            <div className="text-3xl font-bold text-white mb-1">142</div>
            <div className="text-sm text-zinc-400">Total Tenants</div>
          </div>
          <div className="bg-zinc-900/50 border border-white/5 rounded-xl p-6">
            <div className="text-zinc-500 mb-2"><Activity className="w-5 h-5" /></div>
            <div className="text-3xl font-bold text-white mb-1">$4,850</div>
            <div className="text-sm text-zinc-400">MRR</div>
          </div>
          <div className="bg-zinc-900/50 border border-white/5 rounded-xl p-6">
            <div className="text-zinc-500 mb-2"><Database className="w-5 h-5" /></div>
            <div className="text-3xl font-bold text-white mb-1">2.4M</div>
            <div className="text-sm text-zinc-400">LLM Tokens / day</div>
          </div>
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6">
            <div className="text-red-500 mb-2"><ShieldAlert className="w-5 h-5" /></div>
            <div className="text-3xl font-bold text-red-500 mb-1">2</div>
            <div className="text-sm text-red-400">Suspended Accounts</div>
          </div>
        </section>

        {/* Tenant List */}
        <section className="bg-zinc-900/50 border border-white/5 rounded-xl overflow-hidden">
          <div className="p-6 border-b border-white/5">
            <h2 className="text-lg font-semibold text-white">Список клиентов (Tenants)</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/5 bg-zinc-950/50">
                  <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Название</th>
                  <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Статус</th>
                  <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Агенты</th>
                  <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Диалоги</th>
                  <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">MRR</th>
                  <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Действия</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {tenants.map((t) => (
                  <tr key={t.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">{t.name}<br/><span className="text-xs text-zinc-500 font-mono">{t.id}</span></td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusPill tone={t.status === "active" ? "ok" : t.status === "trialing" ? "warn" : "danger"}>
                        {t.status}
                      </StatusPill>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-400">{t.agents}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-400">{t.convs}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-emerald-400 font-medium">{t.mrr}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <button className="text-zinc-400 hover:text-white transition-colors underline underline-offset-4 decoration-zinc-700 hover:decoration-white">
                        Управлять
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

      </div>
    </DashboardShell>
  );
}
