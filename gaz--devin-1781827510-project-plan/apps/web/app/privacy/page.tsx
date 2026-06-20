import Link from "next/link";
import { ArrowLeft, LockKeyhole, ShieldCheck } from "lucide-react";

export const metadata = {
  title: "Конфиденциальность — CallForce",
};

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-black text-white">
      <header className="border-b border-white/5 bg-zinc-950/80">
        <div className="mx-auto flex h-16 max-w-4xl items-center justify-between px-6">
          <Link href="/" className="flex items-center gap-2 text-sm font-medium text-zinc-400 transition-colors hover:text-white">
            <ArrowLeft className="h-4 w-4" />
            На главную
          </Link>
          <ShieldCheck className="h-5 w-5 text-emerald-400" />
        </div>
      </header>

      <article className="mx-auto max-w-4xl px-6 py-16">
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10 text-white">
            <LockKeyhole className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-emerald-400">152-ФЗ ready</p>
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Политика конфиденциальности</h1>
          </div>
        </div>

        <div className="space-y-6 text-sm leading-7 text-zinc-300">
          <p>
            CallForce обрабатывает данные клиентов и операторов только для настройки AI-агентов, ведения диалогов,
            аналитики качества и исполнения договорных обязательств.
          </p>
          <p>
            В продуктовой архитектуре предусмотрены изоляция tenant-ов, bearer auth, audit events, минимизация PII,
            маскирование чувствительных полей в логах и контроль доступа к workspace.
          </p>
          <p>
            Для production-запуска остаются обязательными юридическая финализация документов, регламент хранения данных,
            DPA с поставщиками инфраструктуры и включение rate limiting/password reset/email verification из roadmap.
          </p>
        </div>
      </article>
    </main>
  );
}
