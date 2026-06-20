import { loginAction } from "../actions";
import Link from "next/link";
import { ArrowLeft, KeyRound, Mail } from "lucide-react";
import { SubmitButton } from "../components/SubmitButton";
import { ActionNotice } from "../components/ActionNotice";

export const metadata = {
  title: "Вход — CallForce",
};

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ notice?: string }>;
}) {
  const { notice } = await searchParams;

  return (
    <main className="min-h-screen bg-black flex items-center justify-center p-6 relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-zinc-800/20 blur-[120px] rounded-full pointer-events-none" />

      <Link
        href="/"
        className="absolute top-8 left-8 flex items-center gap-2 text-sm font-medium text-zinc-400 hover:text-white transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        На главную
      </Link>

      <div className="w-full max-w-md bg-zinc-950/50 border border-white/10 rounded-2xl p-8 backdrop-blur-xl relative z-10 shadow-2xl">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-3 mb-6">
            <div className="w-8 h-8 rounded bg-white text-black flex items-center justify-center font-bold text-sm tracking-tighter">
              CF
            </div>
            <span className="font-bold text-xl tracking-tight text-white">
              CallForce
            </span>
          </Link>
          <h1 className="text-2xl font-bold tracking-tight text-white mb-2">С возвращением</h1>
          <p className="text-zinc-400 text-sm">Войдите в панель управления агентами</p>
        </div>

        <ActionNotice notice={notice} />

        <form action={loginAction} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-zinc-300" htmlFor="email">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                className="w-full bg-black border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors"
                type="email"
                id="email"
                name="email"
                placeholder="name@company.com"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-sm font-medium text-zinc-300" htmlFor="password">Пароль</label>
              <Link href="/forgot-password" className="text-xs font-medium text-zinc-400 hover:text-white transition-colors border-b border-transparent hover:border-white">
                Забыли пароль?
              </Link>
            </div>
            <div className="relative">
              <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                className="w-full bg-black border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors"
                type="password"
                id="password"
                name="password"
                placeholder="••••••••"
                required
              />
            </div>
          </div>

          <SubmitButton
            className="w-full bg-white text-black font-medium py-2.5 rounded-lg hover:bg-zinc-200 transition-colors mt-2"
          >
            Войти
          </SubmitButton>
        </form>

        <div className="text-center mt-8 text-sm text-zinc-500">
          Нет аккаунта?{" "}
          <Link href="/register" className="text-white hover:text-emerald-400 font-medium transition-colors">
            Зарегистрироваться
          </Link>
        </div>
      </div>
    </main>
  );
}
