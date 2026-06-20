import Link from "next/link";
import { ArrowLeft, Mail } from "lucide-react";
import { SubmitButton } from "../components/SubmitButton";
import { requestPasswordResetAction } from "../actions";

export const metadata = {
  title: "Восстановление пароля — CallForce",
};

type ForgotPasswordPageProps = {
  searchParams?: Promise<{
    notice?: string;
  }>;
};

function noticeView(notice?: string) {
  if (notice === "reset-sent") {
    return (
      <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
        Если email есть в системе, мы отправили ссылку для сброса пароля.
      </div>
    );
  }

  if (notice === "reset-invalid") {
    return (
      <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
        Введите корректный email.
      </div>
    );
  }

  if (notice === "reset-error") {
    return (
      <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
        Не удалось отправить ссылку. Проверьте Core API и попробуйте ещё раз.
      </div>
    );
  }

  return null;
}

export default async function ForgotPasswordPage({ searchParams }: ForgotPasswordPageProps) {
  const notice = (await searchParams)?.notice;

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-black p-6">
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[36rem] w-[36rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-zinc-800/20 blur-[120px]" />

      <Link
        href="/login"
        className="absolute left-6 top-6 flex items-center gap-2 text-sm font-medium text-zinc-400 transition-colors hover:text-white sm:left-8 sm:top-8"
      >
        <ArrowLeft className="h-4 w-4" />
        Ко входу
      </Link>

      <section className="relative z-10 w-full max-w-md rounded-xl border border-white/10 bg-zinc-950/60 p-8 shadow-2xl backdrop-blur-xl">
        <div className="mb-8 text-center">
          <Link href="/" className="mb-6 inline-flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded bg-white text-sm font-bold tracking-tighter text-black">
              CF
            </div>
            <span className="text-xl font-bold tracking-tight text-white">CallForce</span>
          </Link>
          <h1 className="mb-2 text-2xl font-bold tracking-tight text-white">Восстановление пароля</h1>
          <p className="text-sm text-zinc-400">Отправим безопасную ссылку для смены пароля.</p>
        </div>

        <div className="mb-5">{noticeView(notice)}</div>

        <form action={requestPasswordResetAction} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-zinc-300" htmlFor="email">
              Email
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
              <input
                autoComplete="email"
                className="w-full rounded-lg border border-white/10 bg-black py-2.5 pl-10 pr-4 text-sm text-white placeholder-zinc-500 transition-colors focus:border-emerald-500 focus:outline-none"
                id="email"
                name="email"
                placeholder="name@company.com"
                required
                type="email"
              />
            </div>
          </div>

          <SubmitButton
            className="w-full bg-white text-black font-medium py-2.5 rounded-lg hover:bg-zinc-200 transition-colors mt-2"
          >
            Отправить инструкции
          </SubmitButton>
        </form>
      </section>
    </main>
  );
}
