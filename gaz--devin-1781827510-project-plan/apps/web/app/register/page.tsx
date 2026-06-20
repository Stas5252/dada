import { registerAction } from "../actions";
import Link from "next/link";
import { ArrowLeft, Building2, KeyRound, Mail, User } from "lucide-react";
import { SubmitButton } from "../components/SubmitButton";
import { ActionNotice } from "../components/ActionNotice";

export const metadata = {
  title: "Регистрация — CallForce",
};

export default async function RegisterPage({
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

      <div className="w-full max-w-lg bg-zinc-950/50 border border-white/10 rounded-2xl p-8 backdrop-blur-xl relative z-10 shadow-2xl my-8">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-3 mb-6">
            <div className="w-8 h-8 rounded bg-white text-black flex items-center justify-center font-bold text-sm tracking-tighter">
              CF
            </div>
            <span className="font-bold text-xl tracking-tight text-white">
              CallForce
            </span>
          </Link>
          <h1 className="text-2xl font-bold tracking-tight text-white mb-2">Создайте аккаунт</h1>
          <p className="text-zinc-400 text-sm">Начните автоматизировать коммуникации с AI</p>
        </div>

        <ActionNotice notice={notice} />

        <form action={registerAction} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-300" htmlFor="owner_name">Ваше имя</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                <input
                  className="w-full bg-black border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors"
                  type="text"
                  id="owner_name"
                  name="owner_name"
                  required
                  placeholder="Иван Иванов"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-300" htmlFor="company_name">Компания</label>
              <div className="relative">
                <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                <input
                  className="w-full bg-black border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors"
                  type="text"
                  id="company_name"
                  name="company_name"
                  required
                  placeholder="ООО Ромашка"
                />
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-zinc-300" htmlFor="owner_email">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                className="w-full bg-black border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors"
                type="email"
                id="owner_email"
                name="owner_email"
                required
                placeholder="name@company.com"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-zinc-300" htmlFor="password">Пароль</label>
            <div className="relative">
              <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                className="w-full bg-black border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors"
                type="password"
                id="password"
                name="password"
                required
                placeholder="Минимум 8 символов"
                minLength={8}
              />
            </div>
          </div>

          <SubmitButton
            className="w-full bg-white text-black font-medium py-2.5 rounded-lg hover:bg-zinc-200 transition-colors mt-4"
          >
            Создать аккаунт
          </SubmitButton>
        </form>

        <div className="text-center mt-8 text-sm text-zinc-500">
          Уже есть аккаунт?{" "}
          <Link href="/login" className="text-white hover:text-emerald-400 font-medium transition-colors">
            Войти
          </Link>
        </div>
      </div>
    </main>
  );
}
