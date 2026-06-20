import Link from "next/link";
import { ArrowLeft, CheckCircle2, ShieldAlert } from "lucide-react";
import { mutateCoreApiNoContent } from "../../lib/core-api";

export const metadata = {
  title: "Подтверждение email — CallForce",
};

type VerifyEmailPageProps = {
  searchParams?: Promise<{
    token?: string;
  }>;
};

export default async function VerifyEmailPage({ searchParams }: VerifyEmailPageProps) {
  const token = (await searchParams)?.token ?? "";
  const result = token
    ? await mutateCoreApiNoContent("/api/v1/auth/verify-email", { token })
    : null;
  const verified = result?.state === "live";

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-black p-6 text-white">
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[36rem] w-[36rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-zinc-800/20 blur-[120px]" />

      <Link
        href="/"
        className="absolute left-6 top-6 flex items-center gap-2 text-sm font-medium text-zinc-400 transition-colors hover:text-white sm:left-8 sm:top-8"
      >
        <ArrowLeft className="h-4 w-4" />
        На главную
      </Link>

      <section className="relative z-10 w-full max-w-md rounded-xl border border-white/10 bg-zinc-950/60 p-8 text-center shadow-2xl backdrop-blur-xl">
        <div
          className={`mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full ${
            verified ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-300"
          }`}
        >
          {verified ? <CheckCircle2 className="h-7 w-7" /> : <ShieldAlert className="h-7 w-7" />}
        </div>

        <h1 className="mb-3 text-2xl font-bold tracking-tight">
          {verified ? "Email подтверждён" : "Не удалось подтвердить email"}
        </h1>
        <p className="mb-8 text-sm leading-6 text-zinc-400">
          {verified
            ? "Аккаунт готов к полноценному использованию workspace."
            : "Ссылка отсутствует, истекла или уже была использована."}
        </p>

        <Link
          href="/dashboard"
          className="inline-flex w-full items-center justify-center rounded-lg bg-white px-4 py-2.5 text-sm font-medium text-black transition-colors hover:bg-zinc-200"
        >
          Перейти в кабинет
        </Link>
      </section>
    </main>
  );
}
