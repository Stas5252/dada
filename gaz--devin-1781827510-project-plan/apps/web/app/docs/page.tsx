import Link from "next/link";
import { ArrowLeft, BookOpen, CheckCircle2, Database, MessageSquare, ShieldCheck } from "lucide-react";

export const metadata = {
  title: "Документация — CallForce",
};

const sections = [
  {
    icon: MessageSquare,
    title: "Запуск агента",
    text: "Создайте AI-агента, выберите канал, задайте system prompt и проверьте ответы в Test Console.",
  },
  {
    icon: Database,
    title: "База знаний",
    text: "Загрузите FAQ, меню, регламенты и тексты сайта. RAG-пайплайн индексирует источники для ответов с опорой на факты.",
  },
  {
    icon: ShieldCheck,
    title: "Безопасность",
    text: "Tenant isolation, bearer auth, audit events и подготовка к 152-ФЗ заложены в Core API и дорожную карту.",
  },
];

export default function DocsPage() {
  return (
    <main className="min-h-screen bg-black text-white">
      <header className="border-b border-white/5 bg-zinc-950/80">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-6">
          <Link href="/" className="flex items-center gap-2 text-sm font-medium text-zinc-400 transition-colors hover:text-white">
            <ArrowLeft className="h-4 w-4" />
            На главную
          </Link>
          <Link href="/login" className="rounded-md bg-white px-4 py-2 text-sm font-medium text-black transition-colors hover:bg-zinc-200">
            Войти
          </Link>
        </div>
      </header>

      <section className="mx-auto max-w-5xl px-6 py-16">
        <div className="mb-10 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10 text-white">
            <BookOpen className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-emerald-400">Документация</p>
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">CallForce MVP Guide</h1>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {sections.map((section) => (
            <article key={section.title} className="rounded-xl border border-white/5 bg-zinc-900/50 p-6">
              <section.icon className="mb-5 h-6 w-6 text-emerald-400" />
              <h2 className="mb-3 text-lg font-semibold">{section.title}</h2>
              <p className="text-sm leading-6 text-zinc-400">{section.text}</p>
            </article>
          ))}
        </div>

        <section className="mt-10 rounded-xl border border-white/5 bg-zinc-900/50 p-6">
          <h2 className="mb-4 text-xl font-semibold">Быстрый путь</h2>
          <div className="grid gap-3 text-sm text-zinc-300 sm:grid-cols-2">
            {[
              "Зарегистрировать workspace или войти в demo tenant.",
              "Создать draft агента и заполнить prompt без prefilled текста.",
              "Добавить источник знаний или загрузить файл.",
              "Отправить тестовый вопрос и открыть transcript диалога.",
            ].map((item) => (
              <div key={item} className="flex gap-3">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}
