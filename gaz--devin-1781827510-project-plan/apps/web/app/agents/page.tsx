import Link from "next/link";
import { publishAgentAction } from "../actions";
import { ActionNotice } from "../components/ActionNotice";
import { DashboardShell } from "../components/DashboardShell";
import { EmptyState } from "../components/EmptyState";
import { ResultNotice } from "../components/ResultNotice";
import { StatusPill } from "../components/StatusPill";
import { getAgents } from "../../lib/mvp-data";
import { Plus, Bot, Settings2, Play, UploadCloud } from "lucide-react";

type AgentsPageProps = {
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

export default async function AgentsPage({ searchParams }: AgentsPageProps) {
  const agentsResult = await getAgents();
  const notice = (await searchParams)?.notice;

  return (
    <DashboardShell
      activePath="/agents"
      eyebrow="AI-Агенты"
      title="Список агентов"
      description="Управляйте голосовыми и текстовыми ИИ-ассистентами (состояния Draft, Test, Published)."
      actions={
        <Link
          href="/agents/new"
          className="flex items-center gap-2 bg-white text-black px-4 py-2 rounded-lg text-sm font-medium hover:bg-zinc-200 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Создать агента
        </Link>
      }
    >
      <div className="space-y-6">
        <ActionNotice notice={notice} />
        <ResultNotice result={agentsResult} />

        {agentsResult.data.length > 0 ? (
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-6">
            {agentsResult.data.map((agent) => (
              <article key={agent.id} className="bg-zinc-900/50 border border-white/5 rounded-xl overflow-hidden hover:bg-white/[0.04] transition-colors group">
                <div className="p-6 border-b border-white/5">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
                        <Bot className="w-5 h-5" />
                      </div>
                      <div>
                        <h2 className="text-lg font-semibold text-white">{agent.name}</h2>
                        <div className="text-xs text-zinc-500 font-mono">v{agent.version}</div>
                      </div>
                    </div>
                    <StatusPill tone={agentTone(agent.status)}>{agent.status}</StatusPill>
                  </div>
                  <p className="text-sm text-zinc-400 line-clamp-2 min-h-[40px]">
                    {agent.goal}
                  </p>
                </div>

                <div className="px-6 py-4 border-b border-white/5 bg-black/20">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-xs text-zinc-500 mb-1">Каналы</div>
                      <div className="text-sm text-zinc-300 font-medium">
                        {agent.channels.join(", ")}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500 mb-1">Обновлен</div>
                      <div className="text-sm text-zinc-300">
                        {agent.updatedAt}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="p-4 flex items-center gap-2 bg-zinc-950/50">
                  <Link
                    href={`/agents/${agent.id}`}
                    className="flex-1 flex justify-center items-center gap-2 bg-white/5 hover:bg-white/10 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors"
                  >
                    <Settings2 className="w-4 h-4" /> Edit
                  </Link>
                  <Link
                    href={`/test-console?agentId=${agent.id}`}
                    className="flex-1 flex justify-center items-center gap-2 bg-white/5 hover:bg-white/10 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors"
                  >
                    <Play className="w-4 h-4" /> Test
                  </Link>
                  <form action={publishAgentAction} className="flex-1">
                    <input name="agent_id" type="hidden" value={agent.id} />
                    <input name="return_to" type="hidden" value="/agents" />
                    <button
                      type="submit"
                      disabled={agent.status === "published"}
                      className={`flex w-full justify-center items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        agent.status === "published"
                          ? "bg-emerald-500/10 text-emerald-400 cursor-default"
                          : "bg-white text-black hover:bg-zinc-200"
                      }`}
                    >
                      <UploadCloud className="w-4 h-4" />
                      {agent.status === "published" ? "Live" : "Publish"}
                    </button>
                  </form>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState
            actionHref="/agents/new"
            actionLabel="Создать первого агента"
            description="После настройки здесь появятся агенты, готовые к работе с клиентами."
            title="Агентов пока нет"
          />
        )}
      </div>
    </DashboardShell>
  );
}
