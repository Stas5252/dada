import { loginMfaAction } from "../../actions";
import Link from "next/link";
import { ArrowLeft, Shield } from "lucide-react";

export const metadata = {
  title: "Двухфакторная аутентификация — CallForce",
};

export default async function LoginMfaPage({
  searchParams,
}: {
  searchParams: Promise<{ notice?: string }>;
}) {
  const { notice } = await searchParams;

  return (
    <main className="min-h-screen bg-black flex items-center justify-center p-6 relative overflow-hidden">
      <Link
        href="/login"
        className="absolute top-8 left-8 flex items-center gap-2 text-sm font-medium text-zinc-400 hover:text-white transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Вернуться ко входу
      </Link>

      <div className="w-full max-w-md bg-zinc-950/50 border border-white/10 rounded-lg p-8 backdrop-blur-xl relative z-10 shadow-2xl">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-emerald-500/10 mb-4">
            <Shield className="w-6 h-6 text-emerald-500" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white mb-2">Требуется MFA</h1>
          <p className="text-zinc-400 text-sm">Введите код из приложения-аутентификатора или recovery code</p>
        </div>

        {notice === "mfa-invalid" && (
          <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm font-medium text-center">
            Введите 6-значный код или recovery code
          </div>
        )}
        {notice === "mfa-error" && (
          <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm font-medium text-center">
            Неверный код
          </div>
        )}

        <form action={loginMfaAction} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-zinc-300" htmlFor="code">Код аутентификации</label>
            <input
              className="w-full bg-black border border-white/10 rounded-lg px-4 py-2.5 text-center text-lg font-mono text-white placeholder-zinc-700 focus:outline-none focus:border-emerald-500 transition-colors"
              type="text"
              id="code"
              name="code"
              placeholder="000000 / ABCD-EFGH"
              maxLength={32}
              autoComplete="one-time-code"
              autoCapitalize="characters"
              spellCheck={false}
              required
            />
          </div>

          <button
            type="submit"
            className="w-full bg-white text-black font-medium py-2.5 rounded-lg hover:bg-zinc-200 transition-colors mt-4"
          >
            Подтвердить
          </button>
        </form>
      </div>
    </main>
  );
}
