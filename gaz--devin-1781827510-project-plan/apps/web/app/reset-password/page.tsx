import Link from "next/link";
import { ArrowLeft, KeyRound } from "lucide-react";
import { SubmitButton } from "../components/SubmitButton";
import { resetPasswordAction } from "../actions";

export const metadata = {
  title: "Новый пароль — CallForce",
};

type ResetPasswordPageProps = {
  searchParams?: Promise<{
    notice?: string;
    token?: string;
  }>;
};

function resetNotice(notice?: string) {
  if (notice === "reset-invalid") {
    return (
      <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
        Проверьте токен и убедитесь, что пароли совпадают и содержат минимум 8 символов.
      </div>
    );
  }

  if (notice === "reset-error") {
    return (
      <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
        Ссылка недействительна или уже использована.
      </div>
    );
  }

  return null;
}

export default async function ResetPasswordPage({ searchParams }: ResetPasswordPageProps) {
  const params = await searchParams;
  const token = params?.token ?? "";

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-black p-6">
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[36rem] w-[36rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-emerald-500/10 blur-[120px]" />

      <Link
        href="/login"
        className="absolute left-6 top-6 flex items-center gap-2 text-sm font-medium text-zinc-400 transition-colors hover:text-white sm:left-8 sm:top-8"
      >
        <ArrowLeft className="h-4 w-4" />
        Ко входу
      </Link>

      <section className="relative z-10 w-full max-w-md rounded-xl border border-white/10 bg-zinc-950/60 p-8 shadow-2xl backdrop-blur-xl">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10">
            <KeyRound className="h-6 w-6 text-emerald-400" />
          </div>
          <h1 className="mb-2 text-2xl font-bold tracking-tight text-white">Создайте новый пароль</h1>
          <p className="text-sm text-zinc-400">После смены пароля войдите заново.</p>
        </div>

        <div className="mb-5">
          {!token ? (
            <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              В ссылке отсутствует reset token.
            </div>
          ) : (
            resetNotice(params?.notice)
          )}
        </div>

        <form action={resetPasswordAction} className="space-y-4">
          <input name="token" type="hidden" value={token} />

          <div className="space-y-2">
            <label className="text-sm font-medium text-zinc-300" htmlFor="new_password">
              Новый пароль
            </label>
            <input
              autoComplete="new-password"
              className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white placeholder-zinc-500 transition-colors focus:border-emerald-500 focus:outline-none"
              disabled={!token}
              id="new_password"
              minLength={8}
              name="new_password"
              placeholder="Минимум 8 символов"
              required
              type="password"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-zinc-300" htmlFor="confirm_password">
              Повторите пароль
            </label>
            <input
              autoComplete="new-password"
              className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white placeholder-zinc-500 transition-colors focus:border-emerald-500 focus:outline-none"
              disabled={!token}
              id="confirm_password"
              minLength={8}
              name="confirm_password"
              placeholder="Ещё раз новый пароль"
              required
              type="password"
            />
          </div>

          <SubmitButton
            disabled={!token}
            className="w-full rounded-lg bg-white py-2.5 font-medium text-black transition-colors hover:bg-zinc-200 disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-zinc-500"
          >
            Сменить пароль
          </SubmitButton>
        </form>
      </section>
    </main>
  );
}
