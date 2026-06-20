import Link from "next/link";
import { DashboardShell } from "../components/DashboardShell";
import { StatusPill } from "../components/StatusPill";
import { getOnboardingItems } from "../../lib/mvp-data";
import { ArrowRight, Plus } from "lucide-react";

function statusTone(status: "done" | "current" | "blocked" | "pending") {
  if (status === "done") {
    return "ok";
  }

  if (status === "blocked") {
    return "danger";
  }

  if (status === "current") {
    return "warn";
  }

  return "neutral";
}

export default async function OnboardingPage() {
  const items = await getOnboardingItems();

  return (
    <DashboardShell
      activePath="/onboarding"
      eyebrow="Онбординг"
      title="Чеклист подключения ресторана"
      description="Путь MVP: tenant → агент → knowledge source → тестовый диалог → публикация."
      actions={
        <Link
          href="/agents/new"
          className="flex items-center gap-2 bg-white text-black px-4 py-2 rounded-lg text-sm font-medium hover:bg-zinc-200 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Создать draft агента
        </Link>
      }
    >
      <div className="space-y-4 max-w-3xl">
        {items.map((item, index) => (
          <article
            key={item.id}
            className="flex gap-4 p-5 bg-zinc-900/50 border border-white/5 rounded-xl hover:border-white/10 transition-colors group sm:gap-5 sm:p-6"
          >
            {/* Step Number */}
            <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-bold border ${
              item.status === 'done'
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                : item.status === 'current'
                  ? 'bg-amber-500/10 border-amber-500/20 text-amber-400 animate-pulse'
                  : item.status === 'blocked'
                    ? 'bg-red-500/10 border-red-500/20 text-red-400'
                    : 'bg-zinc-800 border-zinc-700 text-zinc-500'
            }`}>
              {index + 1}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex flex-col gap-2 mb-2 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
                <h2 className="text-lg font-semibold text-white">{item.title}</h2>
                <StatusPill tone={statusTone(item.status)}>{item.status}</StatusPill>
              </div>
              <p className="text-sm text-zinc-400 mb-4">{item.description}</p>
              <Link
                href={item.href}
                className="inline-flex items-center gap-1.5 text-sm font-medium text-zinc-400 hover:text-white transition-colors group-hover:translate-x-1 duration-300"
              >
                Перейти к шагу
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </article>
        ))}
      </div>
    </DashboardShell>
  );
}
