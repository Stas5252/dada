import Link from "next/link";
import { ArrowLeft, Play, Save, UploadCloud, MessageSquare } from "lucide-react";
import { publishAgentAction, updateAgentAction, connectTelegramAction } from "../../actions";
import { ActionNotice } from "../../components/ActionNotice";
import { DashboardShell } from "../../components/DashboardShell";
import { EmptyState } from "../../components/EmptyState";
import { ResultNotice } from "../../components/ResultNotice";
import { StatusPill } from "../../components/StatusPill";
import { getAgent } from "../../../lib/mvp-data";

type AgentEditPageProps = {
  params: Promise<{
    agentId: string;
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

export default async function AgentEditPage({ params, searchParams }: AgentEditPageProps) {
  const [{ agentId }, resolvedSearchParams] = await Promise.all([params, searchParams]);
  const agentResult = await getAgent(agentId);
  const notice = resolvedSearchParams?.notice;
  const agent = agentResult.data;

  return (
    <DashboardShell
      activePath="/agents"
      eyebrow="Agent Builder"
      title={agent ? agent.name : "Агент не найден"}
      description="Редактирование prompt, канала и публикации агента через live Core API."
      actions={
        <Link
          href="/agents"
          className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-zinc-300 transition-colors hover:bg-white/10 hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          К агентам
        </Link>
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
                </div>
              </form>
            </section>

            <aside className="space-y-6">
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
