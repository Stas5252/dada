import Link from "next/link";
import { ArrowLeft, FileText } from "lucide-react";

export const metadata = {
  title: "Оферта — CallForce",
};

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-black text-white">
      <header className="border-b border-white/5 bg-zinc-950/80">
        <div className="mx-auto flex h-16 max-w-4xl items-center justify-between px-6">
          <Link href="/" className="flex items-center gap-2 text-sm font-medium text-zinc-400 transition-colors hover:text-white">
            <ArrowLeft className="h-4 w-4" />
            На главную
          </Link>
          <FileText className="h-5 w-5 text-emerald-400" />
        </div>
      </header>

      <article className="mx-auto max-w-4xl px-6 py-16">
        <p className="mb-3 text-xs font-medium uppercase tracking-wider text-emerald-400">Коммерческие условия</p>
        <h1 className="mb-8 text-3xl font-bold tracking-tight sm:text-4xl">Оферта CallForce</h1>

        <div className="space-y-6 text-sm leading-7 text-zinc-300">
          <p>
            Страница фиксирует публичные условия MVP-пилота: доступ к workspace, лимиты тарифов, тестирование каналов,
            настройку базы знаний и поддержку в период запуска.
          </p>
          <p>
            Финальные договорные условия, SLA, стоимость интеграций, обработка персональных данных и ответственность
            сторон должны быть утверждены перед production-внедрением у клиента.
          </p>
          <p>
            Для демо-стенда эта страница закрывает пользовательский маршрут из футера и служит заготовкой для юридической
            версии оферты.
          </p>
        </div>
      </article>
    </main>
  );
}
