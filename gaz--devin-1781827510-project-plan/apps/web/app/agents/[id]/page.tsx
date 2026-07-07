import Link from "next/link";
import { AlertTriangle, ArrowLeft, CheckCircle2, GitFork, MessageSquare, Play, Save, ShieldCheck, UploadCloud } from "lucide-react";
import { publishAgentAction, updateAgentAction, connectTelegramAction } from "../../actions";
import { ActionNotice } from "../../components/ActionNotice";
import { DashboardShell } from "../../components/DashboardShell";
import { EmptyState } from "../../components/EmptyState";
import { ResultNotice } from "../../components/ResultNotice";
import { StatusPill } from "../../components/StatusPill";
import type { CoreTestbedCaseReadinessStatus, CoreTestbedReadinessResponse } from "../../../lib/core-api";
import { getAgent, getAgentTestbedReadiness } from "../../../lib/mvp-data";

type AgentEditPageProps = {
  params: Promise<{
    id: string;
  }>;
  searchParams?: Promise<{
    notice?: string;
  }>;
};

function agentTone(status: "archived" | "draft" | "testing" | "published") {
  if (status === "published") return "ok";
  if (status === "archived") return "neutral";
  if (status === "testing") return "warn";
  return "neutral";
}

function testbedTone(status: CoreTestbedReadinessResponse["status"]) {
  return status === "ready" ? "ok" : "warn";
}

function caseTone(status: CoreTestbedCaseReadinessStatus) {
  if (status === "passed") return "ok";
  if (status === "running") return "warn";
  return "danger";
}

function caseLabel(status: CoreTestbedCaseReadinessStatus) {
  const labels: Record<CoreTestbedCaseReadinessStatus, string> = {
    failed: "Failed",
    missing_run: "Missing run",
    passed: "Passed",
    running: "Running",
    stale_run: "Stale",
  };
  return labels[status];
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function TestbedReadinessPanel({
  isLive,
  readiness,
}: {
  isLive: boolean;
  readiness: CoreTestbedReadinessResponse;
}) {
  const latestFailures = readiness.failures.slice(0, 3);

  return (
    <section className="rounded-xl border border-white/5 bg-zinc-900/50 p-6">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-300">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Testbed readiness</h2>
            <p className="mt-1 text-sm text-zinc-400">Quality gate for publish with pass-rate and latest run history.</p>
          </div>
        </div>
        <StatusPill tone={testbedTone(readiness.status)}>{readiness.status.replace("_", " ")}</StatusPill>
      </div>

      {!isLive && (
        <div className="mt-4 flex items-start gap-2 rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-xs text-amber-100">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          Live Testbed readiness is unavailable, fallback data is shown.
        </div>
      )}

      <dl className="mt-5 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-xs text-zinc-500">Pass rate</dt>
          <dd className="mt-1 text-lg font-semibold text-white">
            {formatPercent(readiness.pass_rate)}
            <span className="ml-1 text-xs font-normal text-zinc-500">/ {formatPercent(readiness.required_pass_rate)}</span>
          </dd>
        </div>
        <div>
          <dt className="text-xs text-zinc-500">Cases</dt>
          <dd className="mt-1 text-lg font-semibold text-white">{readiness.passing_cases}/{readiness.total_cases}</dd>
        </div>
        <div>
          <dt className="text-xs text-zinc-500">Running</dt>
          <dd className="mt-1 font-medium text-zinc-200">{readiness.running_cases}</dd>
        </div>
        <div>
          <dt className="text-xs text-zinc-500">Needs rerun</dt>
          <dd className="mt-1 font-medium text-zinc-200">{readiness.stale_cases + readiness.missing_run_cases}</dd>
        </div>
      </dl>

      {readiness.cases.length > 0 && (
        <div className="mt-5 divide-y divide-white/5 border-t border-white/5">
          {readiness.cases.slice(0, 4).map((testCase) => (
            <div key={testCase.test_case_id} className="flex items-start justify-between gap-3 py-3">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-white">{testCase.test_case_name}</div>
                {testCase.required_action && (
                  <div className="mt-1 text-xs leading-5 text-zinc-500">{testCase.required_action}</div>
                )}
              </div>
              <StatusPill tone={caseTone(testCase.status)}>{caseLabel(testCase.status)}</StatusPill>
            </div>
          ))}
        </div>
      )}

      {latestFailures.length > 0 ? (
        <div className="mt-4 space-y-2 border-t border-white/5 pt-4">
          {latestFailures.map((failure) => (
            <div key={`${failure.code}-${failure.test_case_id ?? "global"}`} className="flex items-start gap-2 text-xs leading-5 text-amber-100">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>{failure.test_case_name ? `${failure.test_case_name}: ${failure.message}` : failure.message}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-4 flex items-start gap-2 border-t border-white/5 pt-4 text-xs leading-5 text-emerald-200">
          <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          All active Testbed scenarios are fresh and passing.
        </div>
      )}
    </section>
  );
}

export default async function AgentEditPage({ params, searchParams }: AgentEditPageProps) {
  const [{ id }, resolvedSearchParams] = await Promise.all([params, searchParams]);
  const [agentResult, testbedReadinessResult] = await Promise.all([getAgent(id), getAgentTestbedReadiness(id)]);
  const notice = resolvedSearchParams?.notice;
  const agent = agentResult.data;
  const testbedReadiness = testbedReadinessResult.data;
  const enabledTools = new Set(agent?.enabledTools ?? ["escalate_to_human"]);

  return (
    <DashboardShell
      activePath="/agents"
      eyebrow="Agent Builder"
      title={agent ? agent.name : "Агент не найден"}
      description="Редактирование prompt, канала и публикации агента через live Core API."
      actions={
        <div className="flex gap-2">
          <Link
            href={`/agents/${agent?.id}/pathway`}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-600"
          >
            <GitFork className="h-4 w-4" />
            Конструктор сценария
          </Link>
          <Link
            href="/agents"
            className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-zinc-300 transition-colors hover:bg-white/10 hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            К агентам
          </Link>
        </div>
      }
    >
      <div className="space-y-6">
        <ActionNotice notice={notice} />
        <ResultNotice result={agentResult} />

        {agent ? (
          <div className="grid gap-6 lg:grid-cols-[1.4fr_0.8fr]">
            <section className="rounded-xl border border-white/5 bg-zinc-900/50 p-6">
              <div className="mb-6 flex flex-col gap-3 border-b border-white/5 pb-5 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-white">Конфигурация</h2>
                  <p className="mt-1 text-sm text-zinc-400">
                    Изменение prompt или channel вернет опубликованного агента в draft до новой публикации.
                  </p>
                </div>
                <StatusPill tone={agentTone(agent.status)}>{agent.status}</StatusPill>
              </div>

              <form action={updateAgentAction} className="space-y-6">
                <input name="agent_id" type="hidden" value={agent.id} />
                <input name="return_to" type="hidden" value={`/agents/${agent.id}`} />

                <div className="grid gap-5 sm:grid-cols-2">
                  <label className="space-y-2">
                    <span className="text-sm font-medium text-zinc-300">Название</span>
                    <input
                      className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white outline-none transition-colors placeholder:text-zinc-600 focus:border-emerald-500"
                      name="name"
                      defaultValue={agent.name}
                      required
                    />
                  </label>

                  <label className="space-y-2">
                    <span className="text-sm font-medium text-zinc-300">Основной канал</span>
                    <select
                      className="w-full appearance-none rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white outline-none transition-colors focus:border-emerald-500"
                      defaultValue={agent.channel}
                      name="channel"
                    >
                      <option value="telegram">Telegram</option>
                      <option value="web_widget">Web widget</option>
                      <option value="sip">SIP voice</option>
                    </select>
                  </label>
                </div>

                <div className="space-y-5 border-t border-white/5 pt-5">
                  <div className="grid gap-5 sm:grid-cols-3">
                    <label className="space-y-2">
                      <span className="text-sm font-medium text-zinc-300">Role</span>
                      <select
                        className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white outline-none transition-colors focus:border-emerald-500"
                        defaultValue={agent.agentRole}
                        name="agent_role"
                      >
                        <option value="customer_support">Support</option>
                        <option value="sales_consultant">Sales consultant</option>
                        <option value="receptionist">Receptionist</option>
                        <option value="qa_supervisor">QA supervisor</option>
                      </select>
                    </label>
                    <label className="space-y-2">
                      <span className="text-sm font-medium text-zinc-300">Tone</span>
                      <select
                        className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white outline-none transition-colors focus:border-emerald-500"
                        defaultValue={agent.agentTone}
                        name="agent_tone"
                      >
                        <option value="professional">Professional</option>
                        <option value="friendly">Friendly</option>
                        <option value="concise">Concise</option>
                        <option value="premium">Premium</option>
                      </select>
                    </label>
                    <label className="space-y-2">
                      <span className="text-sm font-medium text-zinc-300">Language</span>
                      <select
                        className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white outline-none transition-colors focus:border-emerald-500"
                        defaultValue={agent.agentLanguage}
                        name="agent_language"
                      >
                        <option value="ru">RU</option>
                        <option value="en">EN</option>
                        <option value="mixed_ru_en">RU + EN</option>
                      </select>
                    </label>
                  </div>

                  <label className="block space-y-2">
                    <span className="text-sm font-medium text-zinc-300">Business profile</span>
                    <textarea
                      className="min-h-28 w-full resize-y rounded-lg border border-white/10 bg-black px-4 py-3 text-sm leading-6 text-white outline-none transition-colors placeholder:text-zinc-600 focus:border-emerald-500"
                      name="business_profile"
                      defaultValue={agent.businessProfile}
                    />
                  </label>

                  <div className="grid gap-5 sm:grid-cols-3">
                    <label className="space-y-2">
                      <span className="text-sm font-medium text-zinc-300">Business hours</span>
                      <textarea
                        className="min-h-24 w-full resize-y rounded-lg border border-white/10 bg-black px-4 py-3 text-sm leading-6 text-white outline-none transition-colors placeholder:text-zinc-600 focus:border-emerald-500"
                        name="business_hours"
                        defaultValue={agent.businessHours}
                      />
                    </label>
                    <label className="space-y-2">
                      <span className="text-sm font-medium text-zinc-300">Escalation rules</span>
                      <textarea
                        className="min-h-24 w-full resize-y rounded-lg border border-white/10 bg-black px-4 py-3 text-sm leading-6 text-white outline-none transition-colors placeholder:text-zinc-600 focus:border-emerald-500"
                        name="escalation_rules"
                        defaultValue={agent.escalationRules}
                      />
                    </label>
                    <label className="space-y-2">
                      <span className="text-sm font-medium text-zinc-300">Sales rules</span>
                      <textarea
                        className="min-h-24 w-full resize-y rounded-lg border border-white/10 bg-black px-4 py-3 text-sm leading-6 text-white outline-none transition-colors placeholder:text-zinc-600 focus:border-emerald-500"
                        name="sales_rules"
                        defaultValue={agent.salesRules}
                      />
                    </label>
                  </div>

                  <label className="block space-y-2">
                    <span className="text-sm font-medium text-zinc-300">Forbidden topics</span>
                    <textarea
                      className="min-h-24 w-full resize-y rounded-lg border border-white/10 bg-black px-4 py-3 text-sm leading-6 text-white outline-none transition-colors placeholder:text-zinc-600 focus:border-emerald-500"
                      name="forbidden_topics"
                      defaultValue={agent.forbiddenTopics.join("\n")}
                    />
                  </label>

                  <div className="space-y-3">
                    <input name="enabled_tools" type="hidden" value="escalate_to_human" />
                    <h3 className="text-sm font-semibold text-white">Enabled tools</h3>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {[
                        ["add_to_cart", "Add order item"],
                        ["remove_from_cart", "Remove order item"],
                        ["checkout_cart", "Collect checkout details"],
                        ["confirm_order", "Confirm order"],
                      ].map(([value, label]) => (
                        <label
                          key={value}
                          className="flex min-h-11 items-center gap-3 rounded-lg border border-white/10 bg-black px-3 py-2 text-sm text-zinc-300"
                        >
                          <input
                            className="h-4 w-4 rounded border-white/20 bg-black text-emerald-500 focus:ring-emerald-500/40"
                            defaultChecked={enabledTools.has(value)}
                            name="enabled_tools"
                            type="checkbox"
                            value={value}
                          />
                          {label}
                        </label>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="grid gap-5 sm:grid-cols-3 border-t border-white/5 pt-5">
                  <label className="space-y-2">
                    <span className="text-sm font-medium text-zinc-300">ID Голоса</span>
                    <select
                      className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white outline-none transition-colors focus:border-emerald-500"
                      defaultValue={agent.voiceId}
                      name="voice_id"
                    >
                      <option value="alloy">Alloy (Balanced)</option>
                      <option value="echo">Echo (Warm)</option>
                      <option value="fable">Fable (Narrator)</option>
                      <option value="onyx">Onyx (Deep)</option>
                      <option value="nova">Nova (Bright)</option>
                      <option value="shimmer">Shimmer (Professional)</option>
                    </select>
                  </label>

                  <label className="space-y-2">
                    <span className="text-sm font-medium text-zinc-300">Язык</span>
                    <select
                      className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white outline-none transition-colors focus:border-emerald-500"
                      defaultValue={agent.voiceLanguage}
                      name="voice_language"
                    >
                      <option value="ru">Русский (RU)</option>
                      <option value="en">English (EN)</option>
                      <option value="es">Español (ES)</option>
                    </select>
                  </label>

                  <label className="space-y-2">
                    <span className="text-sm font-medium text-zinc-300">Скорость речи</span>
                    <input
                      type="number"
                      step="0.1"
                      min="0.5"
                      max="2.0"
                      className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white outline-none transition-colors focus:border-emerald-500"
                      name="voice_speed"
                      defaultValue={agent.voiceSpeed}
                      required
                    />
                  </label>
                </div>

                <div className="grid gap-5 sm:grid-cols-3 border-t border-white/5 pt-5">
                  <label className="space-y-2">
                    <span className="text-sm font-medium text-zinc-300">Модель LLM</span>
                    <select
                      className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white outline-none transition-colors focus:border-emerald-500"
                      defaultValue={agent.modelName}
                      name="model_name"
                    >
                      <option value="gpt-4o-mini">gpt-4o-mini (Fast)</option>
                      <option value="gpt-4o">gpt-4o (Smart)</option>
                    </select>
                  </label>

                  <label className="space-y-2">
                    <span className="text-sm font-medium text-zinc-300">Температура</span>
                    <input
                      type="number"
                      step="0.1"
                      min="0.0"
                      max="2.0"
                      className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white outline-none transition-colors focus:border-emerald-500"
                      name="temperature"
                      defaultValue={agent.temperature}
                      required
                    />
                  </label>

                  <label className="space-y-2">
                    <span className="text-sm font-medium text-zinc-300">Max tokens</span>
                    <input
                      type="number"
                      min="100"
                      max="4000"
                      className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white outline-none transition-colors focus:border-emerald-500"
                      name="max_tokens"
                      defaultValue={agent.maxTokens}
                      required
                    />
                  </label>
                </div>

                <label className="block space-y-2">
                  <span className="text-sm font-medium text-zinc-300">System prompt</span>
                  <textarea
                    className="min-h-56 w-full resize-y rounded-lg border border-white/10 bg-black px-4 py-3 text-sm leading-6 text-white outline-none transition-colors placeholder:text-zinc-600 focus:border-emerald-500"
                    name="prompt"
                    defaultValue={agent.goal}
                    required
                  />
                </label>

                <div className="flex flex-col gap-3 border-t border-white/5 pt-5 sm:flex-row">
                  <button
                    type="submit"
                    className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-2.5 text-sm font-medium text-black transition-colors hover:bg-zinc-200"
                  >
                    <Save className="h-4 w-4" />
                    Сохранить изменения
                  </button>
                  <Link
                    href={`/test-console?agentId=${agent.id}`}
                    className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-medium text-zinc-300 transition-colors hover:bg-white/10 hover:text-white"
                  >
                    <Play className="h-4 w-4" />
                    Протестировать
                  </Link>
                  <Link
                    href={`/agents/${agent.id}/pathway`}
                    className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-medium text-zinc-300 transition-colors hover:bg-white/10 hover:text-white"
                  >
                    <GitFork className="h-4 w-4" />
                    Сценарий (Pathway Builder)
                  </Link>
                </div>
              </form>
            </section>

            <aside className="space-y-6">
              <TestbedReadinessPanel
                isLive={testbedReadinessResult.state === "live"}
                readiness={testbedReadiness}
              />

              <section className="rounded-xl border border-white/5 bg-zinc-900/50 p-6">
                <h2 className="text-lg font-semibold text-white">Публикация</h2>
                <p className="mt-2 text-sm text-zinc-400">
                  Опубликованный агент доступен каналам. Draft-версия безопасна для правок и тестов.
                </p>
                <dl className="mt-5 space-y-3 text-sm">
                  <div className="flex items-center justify-between gap-4">
                    <dt className="text-zinc-500">Версия</dt>
                    <dd className="font-medium text-white">{agent.version}</dd>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <dt className="text-zinc-500">Статус</dt>
                    <dd>
                      <StatusPill tone={agentTone(agent.status)}>{agent.status}</StatusPill>
                    </dd>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <dt className="text-zinc-500">Канал</dt>
                    <dd className="font-medium text-white">{agent.channels.join(", ")}</dd>
                  </div>
                </dl>

                <form action={publishAgentAction} className="mt-6">
                  <input name="agent_id" type="hidden" value={agent.id} />
                  <input name="return_to" type="hidden" value={`/agents/${agent.id}`} />
                  <button
                    type="submit"
                    disabled={agent.status === "published"}
                    className={`inline-flex w-full items-center justify-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium transition-colors ${
                      agent.status === "published"
                        ? "bg-emerald-500/10 text-emerald-400"
                        : "bg-white text-black hover:bg-zinc-200"
                    }`}
                  >
                    <UploadCloud className="h-4 w-4" />
                    {agent.status === "published" ? "Уже опубликован" : "Опубликовать"}
                  </button>
                </form>
              </section>

              {agent.channel === "web_widget" && (
                <section className="rounded-xl border border-white/5 bg-zinc-900/50 p-6">
                  <h2 className="text-lg font-semibold text-white">Установка виджета</h2>
                  <p className="mt-2 text-sm text-zinc-400">
                    Разместите этот код перед закрывающим тегом <code>&lt;/body&gt;</code> на вашем сайте:
                  </p>
                  <div className="mt-4 rounded-lg border border-white/5 bg-black p-3 overflow-x-auto">
                    <pre className="text-xs text-emerald-400 font-mono whitespace-pre-wrap select-all">
{`<script 
  src="${process.env.NEXT_PUBLIC_APP_URL || 'https://callforce.app'}/widget.js" 
  data-agent-id="${agent.id}"
></script>`}
                    </pre>
                  </div>
                </section>
              )}

              {agent.channel === "telegram" && (
                <section className="rounded-xl border border-white/5 bg-zinc-900/50 p-6">
                  <h2 className="text-lg font-semibold text-white">Telegram Setup</h2>
                  <p className="mt-2 text-sm text-zinc-400">
                    Подключите вашего бота, чтобы отвечать клиентам в Telegram. Введите Bot Token от <strong>@BotFather</strong>.
                  </p>
                  <form action={connectTelegramAction} className="mt-4 space-y-3">
                    <input name="agent_id" type="hidden" value={agent.id} />
                    <input name="return_to" type="hidden" value={`/agents/${agent.id}`} />
                    <label className="block">
                      <span className="sr-only">Bot Token</span>
                      <input
                        type="password"
                        name="bot_token"
                        placeholder="1234567890:AAH_XXXXXXXXXXXXXXX"
                        className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white outline-none transition-colors placeholder:text-zinc-600 focus:border-emerald-500"
                        required
                      />
                    </label>
                    <button
                      type="submit"
                      className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-500 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-emerald-400"
                    >
                      <MessageSquare className="h-4 w-4" />
                      Подключить Telegram Бота
                    </button>
                  </form>
                </section>
              )}

              <section className="rounded-xl border border-white/5 bg-zinc-900/50 p-6">
                <h2 className="text-lg font-semibold text-white">QA перед запуском</h2>
                <div className="mt-4 space-y-3 text-sm text-zinc-400">
                  <div className="rounded-lg border border-white/5 bg-black p-3">
                    Prompt должен отвечать только из базы знаний и переводить неизвестные запросы оператору.
                  </div>
                  <div className="rounded-lg border border-white/5 bg-black p-3">
                    После публикации пройдите тестовый диалог и проверьте transcript/sources.
                  </div>
                </div>
              </section>
            </aside>
          </div>
        ) : (
          <EmptyState
            actionHref="/agents"
            actionLabel="Вернуться к агентам"
            description="Проверьте tenant или выберите агента из списка."
            title="Агент не найден"
          />
        )}
      </div>
    </DashboardShell>
  );
}
