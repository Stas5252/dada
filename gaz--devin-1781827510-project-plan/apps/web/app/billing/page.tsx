import { fetchCoreApi, type CoreBillingStatus } from "../../lib/core-api";
import { DashboardShell } from "../components/DashboardShell";
import { CreditCard, Check, Activity, Sparkles, Receipt } from "lucide-react";
import Link from "next/link";

export const metadata = {
  title: "Billing & Plans - CallForce",
};

async function getBillingStatus(): Promise<CoreBillingStatus | null> {
  const result = await fetchCoreApi<CoreBillingStatus>("/api/v1/billing/status");
  if (result.state === "live") return result.data;
  return null;
}

type BillingPageProps = {
  searchParams?: Promise<{
    notice?: string;
  }>;
};

export default async function BillingPage({ searchParams }: BillingPageProps) {
  const resolvedSearchParams = await searchParams;
  const notice = resolvedSearchParams?.notice;
  const status = await getBillingStatus();

  // Fallback demo metrics if not live
  const displayStatus: CoreBillingStatus = status || {
    plan: "business",
    messages_used: 487,
    messages_limit: 1000,
    messages_remaining: 513,
    billing_period_start: new Date().toISOString(),
    limit_exceeded: false,
    conversations_used: 34,
  };

  const percentage =
    displayStatus.messages_limit <= 0
      ? 100
      : Math.min(
          100,
          Math.round((displayStatus.messages_used / displayStatus.messages_limit) * 100),
        );
  const progressClass = displayStatus.limit_exceeded
    ? "bg-gradient-to-r from-rose-500 to-amber-500"
    : "bg-gradient-to-r from-emerald-500 to-purple-500";

  const plans = [
    {
      name: "Start",
      price: "2 990 ₽",
      period: "в месяц",
      description: "Для малого бизнеса — чат-поддержка и базовая автоматизация",
      features: [
        "300 диалогов в месяц",
        "1 AI-агент",
        "Telegram + Web Widget",
        "Базовая база знаний",
        "Базовая аналитика",
        "Поддержка по почте",
      ],
      current: displayStatus.plan.toLowerCase() === "start",
      actionText: "Перейти",
    },
    {
      name: "Business",
      price: "7 990 ₽",
      period: "в месяц",
      description: "Для растущего бизнеса — голос, iiko интеграция, 3 агента",
      features: [
        "1 000 диалогов в месяц",
        "3 AI-агента + голосовые звонки",
        "iiko интеграция (меню, стоп-листы)",
        "3 канала связи (Telegram, WhatsApp, Web)",
        "Расширенная аналитика",
        "3 пользователя в команде",
      ],
      current: displayStatus.plan.toLowerCase() === "business",
      actionText: "Перейти",
      featured: true,
    },
    {
      name: "Pro",
      price: "19 990 ₽",
      period: "в месяц",
      description: "Для серьёзных команд — CRM, сценарии, полная автоматизация",
      features: [
        "4 000 диалогов в месяц",
        "10 AI-агентов",
        "Визуальный конструктор сценариев",
        "CRM интеграции (AmoCRM, Bitrix24)",
        "Продвинутая аналитика и отчёты",
        "Поддержка 24/7",
      ],
      current: displayStatus.plan.toLowerCase() === "pro",
      actionText: "Перейти",
    },
    {
      name: "Enterprise",
      price: "от 49 990 ₽",
      period: "в месяц",
      description: "Для крупных сетей — безлимит, SLA, кастомные модели",
      features: [
        "Безлимитные диалоги",
        "Любое количество AI-агентов",
        "Собственные LLM-модели (on-premise)",
        "Интеграция с r_keeper, 1С, SAP",
        "SLA 99.9% по договору",
        "Выделенный менеджер и доработки",
      ],
      current: displayStatus.plan.toLowerCase() === "enterprise",
      actionText: "Связаться с нами",
    },
  ];

  const invoices = [
    { id: "INV-2026-003", date: "15 июня 2026", amount: "7 990 ₽", plan: "Тариф Business", status: "Paid" },
    { id: "INV-2026-002", date: "15 мая 2026", amount: "7 990 ₽", plan: "Тариф Business", status: "Paid" },
    { id: "INV-2026-001", date: "15 апреля 2026", amount: "7 990 ₽", plan: "Тариф Business", status: "Paid" },
  ];

  return (
    <DashboardShell
      activePath="/billing"
      eyebrow="Биллинг"
      title="Тарифные планы и оплата"
      description="Управляйте подпиской, просматривайте лимиты использования и историю транзакций."
    >
      <div className="space-y-8">
        {notice === "payment-success" && (
          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-medium">
            Оплата успешно произведена через ЮKassa! Ваш тариф обновлен.
          </div>
        )}
        {notice === "payment-failed" && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm font-medium">
            Ошибка при обработке платежа. Попробуйте еще раз.
          </div>
        )}
        {notice === "payment-cancelled" && (
          <div className="p-4 rounded-xl bg-zinc-500/10 border border-zinc-500/20 text-zinc-400 text-sm font-medium">
            Платеж отменен пользователем.
          </div>
        )}

        {/* Usage Overview Card */}
        <section className="p-6 rounded-2xl border border-white/5 bg-zinc-900/50">
          <div className="flex items-center gap-2 mb-4 text-white">
            <Activity className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg font-semibold">Лимиты и использование ресурсов</h2>
          </div>

          <div className="grid md:grid-cols-[1.5fr_1fr] gap-6">
            <div className="space-y-4">
              <div className="flex justify-between items-end text-sm">
                <span className="text-zinc-400">Использовано сообщений в текущем цикле:</span>
                <span className="font-semibold text-white">
                  {displayStatus.messages_used.toLocaleString()} / {displayStatus.messages_limit.toLocaleString()}
                </span>
              </div>
              
              <div className="w-full h-3 bg-black rounded-full overflow-hidden border border-white/5">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${progressClass}`}
                  style={{ width: `${percentage}%` }}
                />
              </div>

              <div className="grid gap-3 text-xs text-zinc-500 sm:grid-cols-3">
                <div>
                  <span className="block text-zinc-600">Осталось</span>
                  <span className="font-semibold text-zinc-300">
                    {displayStatus.messages_remaining.toLocaleString()}
                  </span>
                </div>
                <div>
                  <span className="block text-zinc-600">Период</span>
                  <span className="font-semibold text-zinc-300">
                    {new Date(displayStatus.billing_period_start).toLocaleDateString("ru-RU")}
                  </span>
                </div>
                <div>
                  <span className="block text-zinc-600">Статус</span>
                  <span
                    className={`font-semibold ${displayStatus.limit_exceeded ? "text-rose-300" : "text-emerald-300"}`}
                  >
                    {displayStatus.limit_exceeded ? "Лимит исчерпан" : "Активен"}
                  </span>
                </div>
              </div>

              <p className="text-xs text-zinc-500">
                Лимиты обновляются каждый месяц. При достижении 100% ИИ-агенты временно перестанут отвечать.
              </p>
            </div>

            <div className="flex items-center justify-between p-4 rounded-xl bg-black/40 border border-white/5">
              <div className="space-y-1">
                <span className="text-xs text-zinc-400 font-mono uppercase">Текущий тарифный план</span>
                <div className="flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-amber-400" />
                  <span className="text-xl font-bold text-white uppercase">{displayStatus.plan}</span>
                </div>
              </div>
              <div className="text-right">
                <span className="text-xs text-zinc-400 block">Диалогов всего:</span>
                <span className="text-lg font-bold text-zinc-200">{displayStatus.conversations_used}</span>
              </div>
            </div>
          </div>
        </section>

        {/* Pricing Matrix */}
        <section>
          <div className="flex items-center gap-2 mb-6 text-white">
            <CreditCard className="w-5 h-5 text-purple-400" />
            <h2 className="text-lg font-semibold">Доступные тарифные планы</h2>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {plans.map((p) => (
              <div
                key={p.name}
                className={`p-6 rounded-2xl border flex flex-col justify-between transition-all ${
                  p.current
                    ? "bg-white/[0.03] border-purple-500 shadow-lg shadow-purple-500/10 ring-1 ring-purple-500/30"
                    : (p as Record<string, unknown>).featured
                      ? "bg-zinc-900/50 border-emerald-500/30 hover:border-emerald-500/50 shadow-lg shadow-emerald-500/5"
                      : "bg-zinc-900/30 border-white/5 hover:border-white/10"
                }`}
              >
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="text-lg font-bold text-white">{p.name}</h3>
                    {p.current && (
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                        Активен
                      </span>
                    )}
                  </div>
                  
                  <div className="flex items-baseline gap-1.5 mb-2">
                    <span className="text-2xl font-bold text-white">{p.price}</span>
                    <span className="text-xs text-zinc-500">{p.period}</span>
                  </div>
                  
                  <p className="text-xs text-zinc-400 mb-6 leading-relaxed min-h-[32px]">{p.description}</p>
                  
                  <ul className="space-y-2.5 mb-8 border-t border-white/5 pt-4">
                    {p.features.map((f) => (
                      <li key={f} className="flex gap-2 text-xs text-zinc-300">
                        <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {p.current ? (
                  <button
                    disabled
                    className="w-full py-2.5 rounded-xl text-sm font-semibold bg-white/5 text-zinc-500 border border-white/5 cursor-default"
                  >
                    {p.actionText}
                  </button>
                ) : p.name.toLowerCase() === "enterprise" ? (
                  <Link
                    href="mailto:support@callforce.ru"
                    className="block w-full py-2.5 text-center rounded-xl text-sm font-semibold bg-white text-black hover:bg-zinc-200"
                  >
                    {p.actionText}
                  </Link>
                ) : (
                  <Link
                    href={`/billing/checkout?plan=${p.name.toLowerCase()}`}
                    className={`block w-full py-2.5 text-center rounded-xl text-sm font-semibold transition-all ${
                      p.name === "Business"
                        ? "bg-gradient-to-r from-emerald-500 to-purple-600 hover:from-emerald-400 hover:to-purple-500 text-white shadow-lg"
                        : p.name === "Pro"
                          ? "bg-purple-600 hover:bg-purple-500 text-white"
                          : "bg-white text-black hover:bg-zinc-200"
                    }`}
                  >
                    {p.actionText}
                  </Link>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* Invoice History */}
        <section className="bg-zinc-900/50 border border-white/5 rounded-2xl overflow-hidden">
          <div className="p-4 border-b border-white/5 flex items-center gap-2 text-white bg-zinc-950/20">
            <Receipt className="w-5 h-5 text-zinc-400" />
            <h2 className="text-sm font-semibold">История платежей</h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-white/5 text-zinc-500 text-xs font-mono uppercase">
                  <th className="p-4">ID Счёта</th>
                  <th className="p-4">Дата</th>
                  <th className="p-4">Тариф</th>
                  <th className="p-4">Сумма</th>
                  <th className="p-4">Статус</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-zinc-300">
                {invoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-white/[0.01] transition-colors">
                    <td className="p-4 font-mono text-xs">{inv.id}</td>
                    <td className="p-4">{inv.date}</td>
                    <td className="p-4">{inv.plan}</td>
                    <td className="p-4 font-semibold text-white">{inv.amount}</td>
                    <td className="p-4">
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Оплачен
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
      
      {status === null && (
        <p className="text-xs text-zinc-600 mt-6 text-center">
          Показаны демо-метрики биллинга. Для просмотра живого статуса подключите API.
        </p>
      )}
    </DashboardShell>
  );
}
