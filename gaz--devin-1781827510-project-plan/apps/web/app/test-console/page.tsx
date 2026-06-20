import Link from "next/link";
import { createMockChatAction, createVoicePreviewAction } from "../actions";
import { ActionNotice } from "../components/ActionNotice";
import { DashboardShell } from "../components/DashboardShell";
import { EmptyState } from "../components/EmptyState";
import { ResultNotice } from "../components/ResultNotice";
import { StatusPill } from "../components/StatusPill";
import { VoiceRecorder } from "../components/VoiceRecorder";
import { getAgents, getConversations } from "../../lib/mvp-data";
import { getCoreTenantId } from "../../lib/core-api";
import { Mic2, Send, MessageSquare } from "lucide-react";

type TestConsolePageProps = {
  searchParams?: Promise<{
    agentId?: string;
    notice?: string;
  }>;
};

function conversationTone(status: "draft" | "escalated" | "open" | "resolved") {
  if (status === "resolved") {
    return "ok";
  }

  if (status === "escalated") {
    return "danger";
  }

  return "warn";
}

export default async function TestConsolePage({ searchParams }: TestConsolePageProps) {
  const [agentsResult, conversationsResult, tenantId] = await Promise.all([
    getAgents(),
    getConversations(),
    getCoreTenantId(),
  ]);
  const resolvedSearchParams = await searchParams;
  const notice = resolvedSearchParams?.notice;
  const selectedAgentId = agentsResult.data.some((agent) => agent.id === resolvedSearchParams?.agentId)
    ? resolvedSearchParams?.agentId
    : agentsResult.data[0]?.id;

  return (
    <DashboardShell
      activePath="/test-console"
      eyebrow="Тестирование"
      title="Тестовый диалог"
      description="Проверка Core MVP Chat: сообщение клиента → RAG/no-answer → conversation log."
    >
      <div className="space-y-6">
        <ActionNotice notice={notice} />
        <ResultNotice result={agentsResult} />
        <ResultNotice result={conversationsResult} />

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Test Form */}
          <article className="bg-zinc-900/50 border border-white/5 rounded-xl overflow-hidden p-6">
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-white mb-2">Новый тест</h2>
              <p className="text-sm text-zinc-400">Отправьте вопрос выбранному агенту и откройте созданный transcript.</p>
            </div>
            {agentsResult.data.length > 0 ? (
              <form action={createMockChatAction} className="space-y-5">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-zinc-300">Агент</label>
                  <select
                    name="agent_id"
                    required
                    defaultValue={selectedAgentId}
                    className="w-full bg-black border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500 transition-colors appearance-none"
                  >
                    {agentsResult.data.map((agent) => (
                      <option key={agent.id} value={agent.id}>
                        {agent.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-zinc-300">Канал</label>
                  <select
                    defaultValue="web_widget"
                    name="channel"
                    className="w-full bg-black border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500 transition-colors appearance-none"
                  >
                    <option value="web_widget">Web widget</option>
                    <option value="telegram">Telegram</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-zinc-300">Сообщение клиента</label>
                  <textarea
                    className="w-full bg-black border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors resize-y"
                    defaultValue="Сколько занимает доставка и от какой суммы она бесплатная?"
                    name="message"
                    required
                    rows={5}
                  />
                </div>

                <button
                  type="submit"
                  className="w-full flex items-center justify-center gap-2 bg-white text-black font-medium py-2.5 rounded-lg hover:bg-zinc-200 transition-colors"
                >
                  <Send className="w-4 h-4" />
                  Запустить тест
                </button>
              </form>
            ) : (
              <EmptyState
                actionHref="/agents/new"
                actionLabel="Создать агента"
                description="Для тестового диалога нужен хотя бы один агент."
                title="Нет агентов"
              />
            )}

            <div className="mt-8 border-t border-white/10 pt-8 space-y-8">
              <div>
                <h3 className="text-lg font-medium text-white mb-4">Voice preview</h3>
                {agentsResult.data.length > 0 ? (
                  <form action={createVoicePreviewAction} className="space-y-4">
                    <input
                      name="agent_id"
                      type="hidden"
                      value={selectedAgentId || agentsResult.data[0].id}
                    />
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-zinc-300">
                        Фраза клиента для голосового сценария
                      </label>
                      <textarea
                        className="w-full bg-black border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors resize-y"
                        defaultValue="Здравствуйте, хочу уточнить время доставки и условия оплаты."
                        name="message"
                        required
                        rows={4}
                      />
                    </div>
                    <button
                      type="submit"
                      className="w-full flex items-center justify-center gap-2 bg-emerald-400 text-black font-medium py-2.5 rounded-lg hover:bg-emerald-300 transition-colors"
                    >
                      <Mic2 className="w-4 h-4" />
                      Запустить voice preview
                    </button>
                  </form>
                ) : (
                  <div className="text-sm text-zinc-500">Сначала создайте агента.</div>
                )}
              </div>

              <div className="border-t border-white/10 pt-8">
                <h3 className="text-lg font-medium text-white mb-4">Voice E2E Testing</h3>
              {agentsResult.data.length > 0 ? (
                <VoiceRecorder agentId={selectedAgentId || agentsResult.data[0].id} tenantId={tenantId} />
              ) : (
                <div className="text-sm text-zinc-500">Сначала создайте агента.</div>
              )}
              </div>
            </div>
          </article>

          {/* Recent Results */}
          <article className="bg-zinc-900/50 border border-white/5 rounded-xl overflow-hidden p-6">
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-white mb-2">Последние результаты</h2>
              <p className="text-sm text-zinc-400">История тестовых диалогов.</p>
            </div>
            {conversationsResult.data.length > 0 ? (
              <div className="space-y-3">
                {conversationsResult.data.slice(0, 4).map((conversation) => (
                  <div
                    key={conversation.id}
                    className="flex items-start justify-between gap-4 p-4 rounded-lg bg-black border border-white/5 hover:border-white/10 transition-colors"
                  >
                    <div className="min-w-0 flex-1">
                      <Link
                        href={`/conversations/${conversation.id}`}
                        className="text-sm font-medium text-white hover:text-emerald-400 transition-colors line-clamp-1"
                      >
                        {conversation.summary}
                      </Link>
                      <div className="flex items-center gap-2 mt-1.5">
                        <MessageSquare className="w-3.5 h-3.5 text-zinc-500" />
                        <span className="text-xs text-zinc-500">
                          {conversation.channel} · {conversation.updatedAt}
                        </span>
                      </div>
                    </div>
                    <StatusPill tone={conversationTone(conversation.status)}>
                      {conversation.status}
                    </StatusPill>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-zinc-500 text-center py-8">
                Диалогов пока нет. Отправьте первый тестовый запрос.
              </div>
            )}
          </article>
        </div>
      </div>
    </DashboardShell>
  );
}
