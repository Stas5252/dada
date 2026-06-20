import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  KeyRound,
  LockKeyhole,
  MailCheck,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  ShieldOff,
  Smartphone,
  UserRound,
} from "lucide-react";
import { DashboardShell } from "../../components/DashboardShell";
import { StatusPill } from "../../components/StatusPill";
import {
  cancelMfaSetupAction,
  clearMfaRecoveryCodesAction,
  disableMfaAction,
  regenerateMfaRecoveryCodesAction,
  startMfaSetupAction,
  verifyMfaSetupAction,
} from "../../actions";
import { getMfaRecoveryCodes, getMfaSetup } from "../../../lib/auth";
import { fetchCoreApi, type CoreUser } from "../../../lib/core-api";

export const metadata = {
  title: "Security settings - CallForce",
};

const notices: Record<string, { text: string; title: string; tone: "danger" | "info" }> = {
  "mfa-started": {
    tone: "info",
    title: "MFA setup",
    text: "Секрет создан. Добавьте его в authenticator и подтвердите 6-значным кодом.",
  },
  "mfa-enabled": {
    tone: "info",
    title: "MFA enabled",
    text: "Двухфакторная аутентификация включена. Сохраните recovery codes сейчас.",
  },
  "mfa-recovery-regenerated": {
    tone: "info",
    title: "Recovery codes",
    text: "Новый набор recovery codes создан. Старые коды больше не работают.",
  },
  "mfa-recovery-error": {
    tone: "danger",
    title: "Recovery codes",
    text: "Core API не перевыпустил recovery codes. Проверьте код и попробуйте еще раз.",
  },
  "mfa-disabled": {
    tone: "info",
    title: "MFA disabled",
    text: "Двухфакторная аутентификация выключена для текущего пользователя.",
  },
  "mfa-disable-error": {
    tone: "danger",
    title: "MFA disable",
    text: "Core API не выключил MFA. Проверьте код и попробуйте еще раз.",
  },
  "mfa-cancelled": {
    tone: "info",
    title: "MFA cancelled",
    text: "Черновик настройки MFA удален.",
  },
  "mfa-start-error": {
    tone: "danger",
    title: "MFA setup error",
    text: "Core API не создал секрет MFA. Проверьте авторизацию и попробуйте еще раз.",
  },
  "mfa-code-invalid": {
    tone: "danger",
    title: "MFA code",
    text: "Введите 6 цифр из приложения-аутентификатора или recovery code.",
  },
  "mfa-code-error": {
    tone: "danger",
    title: "MFA code",
    text: "Код не прошел проверку. Обновите код в приложении и повторите попытку.",
  },
  "mfa-setup-missing": {
    tone: "danger",
    title: "MFA setup expired",
    text: "Секрет настройки истек. Запустите настройку MFA заново.",
  },
};

const roleLabels: Record<CoreUser["role"], string> = {
  admin: "Admin",
  agent: "Agent",
  owner: "Owner",
  viewer: "Viewer",
};

function formatDate(value?: string) {
  if (!value) {
    return "Нет данных";
  }

  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function SecurityNotice({ notice }: { notice?: string }) {
  if (!notice) {
    return null;
  }

  const config = notices[notice];

  if (!config) {
    return null;
  }

  const toneClass =
    config.tone === "danger"
      ? "border-red-500/20 bg-red-500/10 text-red-300"
      : "border-emerald-500/20 bg-emerald-500/10 text-emerald-300";

  return (
    <div className={`rounded-lg border px-4 py-3 text-sm ${toneClass}`} role="status">
      <strong className="font-semibold text-white">{config.title}:</strong> {config.text}
    </div>
  );
}

function ReadOnlySecret({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-2">
      <div className="text-xs font-medium uppercase text-zinc-500">{label}</div>
      <code className="block max-w-full overflow-x-auto rounded-lg border border-white/10 bg-black px-3 py-2 text-xs text-zinc-200">
        {value}
      </code>
    </div>
  );
}

export default async function SecuritySettingsPage({
  searchParams,
}: {
  searchParams: Promise<{ notice?: string }>;
}) {
  const [{ notice }, userResult, mfaSetup, mfaRecoveryCodes] = await Promise.all([
    searchParams,
    fetchCoreApi<CoreUser>("/api/v1/auth/me"),
    getMfaSetup(),
    getMfaRecoveryCodes(),
  ]);
  const user = userResult.state === "live" ? userResult.data : null;
  const hasMfaSetup = Boolean(mfaSetup && !user?.mfa_enabled);
  const issuedRecoveryCodes = mfaRecoveryCodes?.codes ?? [];

  return (
    <DashboardShell
      activePath="/settings/security"
      eyebrow="Security"
      title="Безопасность аккаунта"
      description="Контроль доступа, MFA и состояние текущего пользователя workspace."
      actions={
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm font-medium text-zinc-300 transition-colors hover:bg-white/10 hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          Обзор
        </Link>
      }
    >
      <div className="space-y-6">
        <SecurityNotice notice={notice} />

        {userResult.state !== "live" && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            <strong className="font-semibold text-white">Core API:</strong> {userResult.message}
          </div>
        )}

        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border border-white/5 bg-zinc-900/50 p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <UserRound className="h-5 w-5 text-zinc-500" />
              <StatusPill tone={user ? "ok" : "danger"}>{user ? "Live" : "Unavailable"}</StatusPill>
            </div>
            <div className="text-sm text-zinc-500">Пользователь</div>
            <div className="mt-1 truncate text-lg font-semibold text-white">{user?.name ?? "Нет данных"}</div>
            <div className="mt-1 truncate text-sm text-zinc-400">{user?.email ?? "Нет live-сессии"}</div>
          </div>

          <div className="rounded-lg border border-white/5 bg-zinc-900/50 p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <MailCheck className="h-5 w-5 text-zinc-500" />
              <StatusPill tone={user?.email_verified ? "ok" : "warn"}>
                {user?.email_verified ? "Verified" : "Pending"}
              </StatusPill>
            </div>
            <div className="text-sm text-zinc-500">Email</div>
            <div className="mt-1 text-lg font-semibold text-white">
              {user?.email_verified ? "Подтвержден" : "Ожидает подтверждения"}
            </div>
            <div className="mt-1 text-sm text-zinc-400">Создан: {formatDate(user?.created_at)}</div>
          </div>

          <div className="rounded-lg border border-white/5 bg-zinc-900/50 p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <ShieldCheck className="h-5 w-5 text-zinc-500" />
              <StatusPill tone={user?.mfa_enabled ? "ok" : hasMfaSetup ? "warn" : "neutral"}>
                {user?.mfa_enabled ? "Enabled" : hasMfaSetup ? "Setup" : "Off"}
              </StatusPill>
            </div>
            <div className="text-sm text-zinc-500">MFA</div>
            <div className="mt-1 text-lg font-semibold text-white">
              {user?.mfa_enabled ? "Включена" : hasMfaSetup ? "Настройка начата" : "Не включена"}
            </div>
            <div className="mt-1 text-sm text-zinc-400">Роль: {user ? roleLabels[user.role] : "Нет данных"}</div>
            {user?.mfa_enabled && (
              <div className="mt-1 text-sm text-zinc-500">
                Recovery codes: {user.mfa_recovery_codes_remaining}
              </div>
            )}
          </div>
        </section>

        <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <section className="rounded-lg border border-white/5 bg-zinc-900/50 p-6">
            <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-white">Двухфакторная аутентификация</h2>
                <p className="mt-1 text-sm text-zinc-400">
                  Вход в workspace будет требовать одноразовый код после пароля.
                </p>
              </div>
              <StatusPill tone={user?.mfa_enabled ? "ok" : "warn"}>
                {user?.mfa_enabled ? "Protected" : "Action needed"}
              </StatusPill>
            </div>

            {user?.mfa_enabled ? (
              <div className="space-y-6">
                <div className="flex items-start gap-3 text-sm text-emerald-200">
                  <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-emerald-400" />
                  <div>
                    <div className="font-semibold text-white">MFA активна</div>
                    <div className="mt-1 text-emerald-200/80">
                      Следующий вход после пароля перейдет на экран проверки 6-значного кода или recovery code.
                    </div>
                  </div>
                </div>

                {issuedRecoveryCodes.length > 0 && (
                  <div className="space-y-4 border-t border-white/5 pt-5">
                    <div>
                      <h3 className="text-sm font-semibold uppercase text-zinc-400">Recovery codes</h3>
                      <p className="mt-1 text-sm text-zinc-500">
                        Сохраните эти одноразовые коды в менеджере паролей. После ухода со страницы они не будут показаны снова.
                      </p>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {issuedRecoveryCodes.map((code) => (
                        <code
                          className="rounded-md border border-white/10 bg-black px-3 py-2 text-center font-mono text-sm text-zinc-100"
                          key={code}
                        >
                          {code}
                        </code>
                      ))}
                    </div>
                    <form action={clearMfaRecoveryCodesAction}>
                      <button
                        type="submit"
                        className="inline-flex items-center justify-center rounded-lg border border-white/10 px-4 py-2 text-sm font-medium text-zinc-300 transition-colors hover:bg-white/5 hover:text-white"
                      >
                        Я сохранил коды
                      </button>
                    </form>
                  </div>
                )}

                <div className="grid gap-5 border-t border-white/5 pt-5 md:grid-cols-2">
                  <form action={regenerateMfaRecoveryCodesAction} className="space-y-3">
                    <div>
                      <h3 className="text-sm font-semibold text-white">Перевыпустить recovery codes</h3>
                      <p className="mt-1 text-sm text-zinc-500">Старый набор будет отозван сразу после проверки кода.</p>
                    </div>
                    <input
                      className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-center font-mono text-sm text-white outline-none transition-colors placeholder:text-zinc-700 focus:border-emerald-500"
                      name="code"
                      maxLength={32}
                      placeholder="000000 / ABCD-EFGH"
                      required
                      spellCheck={false}
                    />
                    <button
                      type="submit"
                      className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-white/10 px-4 py-2.5 text-sm font-medium text-zinc-300 transition-colors hover:bg-white/5 hover:text-white"
                    >
                      <RefreshCw className="h-4 w-4" />
                      Новый набор
                    </button>
                  </form>

                  <form action={disableMfaAction} className="space-y-3">
                    <div>
                      <h3 className="text-sm font-semibold text-white">Выключить MFA</h3>
                      <p className="mt-1 text-sm text-zinc-500">Требуется текущий TOTP или recovery code владельца сессии.</p>
                    </div>
                    <input
                      className="w-full rounded-lg border border-red-500/20 bg-black px-4 py-3 text-center font-mono text-sm text-white outline-none transition-colors placeholder:text-zinc-700 focus:border-red-500"
                      name="code"
                      maxLength={32}
                      placeholder="000000 / ABCD-EFGH"
                      required
                      spellCheck={false}
                    />
                    <button
                      type="submit"
                      className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-red-500/20 px-4 py-2.5 text-sm font-medium text-red-300 transition-colors hover:bg-red-500/10 hover:text-red-200"
                    >
                      <ShieldOff className="h-4 w-4" />
                      Выключить MFA
                    </button>
                  </form>
                </div>
              </div>
            ) : hasMfaSetup && mfaSetup ? (
              <div className="space-y-5">
                <div className="grid gap-4 md:grid-cols-2">
                  <ReadOnlySecret label="Setup key" value={mfaSetup.secret} />
                  <ReadOnlySecret label="otpauth URI" value={mfaSetup.provisioning_uri} />
                </div>

                <form action={verifyMfaSetupAction} className="grid gap-3 sm:grid-cols-[1fr_auto]">
                  <label className="space-y-2">
                    <span className="text-sm font-medium text-zinc-300">Код подтверждения</span>
                    <input
                      className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-center font-mono text-lg text-white outline-none transition-colors placeholder:text-zinc-700 focus:border-emerald-500"
                      name="code"
                      inputMode="numeric"
                      maxLength={6}
                      pattern="[0-9]{6}"
                      placeholder="000000"
                      required
                    />
                  </label>
                  <button
                    type="submit"
                    className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-medium text-black transition-colors hover:bg-zinc-200 sm:self-end"
                  >
                    <ShieldCheck className="h-4 w-4" />
                    Включить MFA
                  </button>
                </form>

                <form action={cancelMfaSetupAction}>
                  <button
                    type="submit"
                    className="inline-flex items-center justify-center rounded-lg border border-white/10 px-4 py-2 text-sm font-medium text-zinc-300 transition-colors hover:bg-white/5 hover:text-white"
                  >
                    Отменить настройку
                  </button>
                </form>
              </div>
            ) : (
              <form action={startMfaSetupAction}>
                <button
                  type="submit"
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-medium text-black transition-colors hover:bg-zinc-200"
                  disabled={!user}
                >
                  <Smartphone className="h-4 w-4" />
                  Настроить MFA
                </button>
              </form>
            )}
          </section>

          <section className="rounded-lg border border-white/5 bg-zinc-900/50 p-6">
            <h2 className="text-xl font-semibold text-white">Контроль сессии</h2>
            <div className="mt-5 space-y-4">
              <div className="flex items-start gap-3">
                <LockKeyhole className="mt-0.5 h-5 w-5 flex-shrink-0 text-zinc-500" />
                <div>
                  <div className="text-sm font-medium text-white">HTTP-only cookies</div>
                  <div className="mt-1 text-sm text-zinc-400">
                    Access и refresh токены недоступны клиентскому JavaScript.
                  </div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <KeyRound className="mt-0.5 h-5 w-5 flex-shrink-0 text-zinc-500" />
                <div>
                  <div className="text-sm font-medium text-white">Refresh revoke</div>
                  <div className="mt-1 text-sm text-zinc-400">
                    Выход из workspace отзывает refresh session в Core API.
                  </div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                {user?.email_verified ? (
                  <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-emerald-400" />
                ) : (
                  <ShieldAlert className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-400" />
                )}
                <div>
                  <div className="text-sm font-medium text-white">Email verification</div>
                  <div className="mt-1 text-sm text-zinc-400">
                    {user?.email_verified
                      ? "Почта подтверждена."
                      : "Почта еще не подтверждена для текущего пользователя."}
                  </div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <Clock3 className="mt-0.5 h-5 w-5 flex-shrink-0 text-zinc-500" />
                <div>
                  <div className="text-sm font-medium text-white">Updated</div>
                  <div className="mt-1 text-sm text-zinc-400">{formatDate(user?.updated_at)}</div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </DashboardShell>
  );
}
