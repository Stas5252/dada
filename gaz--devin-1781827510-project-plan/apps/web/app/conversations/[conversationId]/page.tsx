import Link from "next/link";
import { notFound } from "next/navigation";
import { ActionNotice } from "../../components/ActionNotice";
import { DashboardShell } from "../../components/DashboardShell";
import { ResultNotice } from "../../components/ResultNotice";
import { StatusPill } from "../../components/StatusPill";
import { getConversationDetail } from "../../../lib/mvp-data";
import { ArrowLeft, Wrench } from "lucide-react";
import { OperatorConsole } from "../../components/OperatorConsole";

function toolTone(status: "success" | "skipped" | "failed") {
  if (status === "success") {
    return "ok";
  }

  if (status === "failed") {
    return "danger";
  }

  return "warn";
}

type ConversationDetailPageProps = {
  params: Promise<{
    conversationId: string;
  }>;
  searchParams?: Promise<{
    notice?: string;
  }>;
};

export default async function ConversationDetailPage({ params, searchParams }: ConversationDetailPageProps) {
  const { conversationId } = await params;
  const notice = (await searchParams)?.notice;
  const conversationResult = await getConversationDetail(conversationId);
  const conversation = conversationResult.data;

  if (!conversation) {
    notFound();
  }

  return (
    <DashboardShell
      activePath="/conversations"
      eyebrow={conversation.channel}
      title={`Диалог ${conversation.id.slice(0, 8)}…`}
      description={conversation.summary}
      actions={
        <Link
          href="/conversations"
          className="flex items-center gap-2 bg-white/5 text-zinc-300 border border-white/10 px-4 py-2 rounded-lg text-sm font-medium hover:bg-white/10 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Назад к списку
        </Link>
      }
    >
      <div className="space-y-6">
        <ActionNotice notice={notice} />
        <ResultNotice result={conversationResult} />

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Summary Card */}
          <article className="bg-zinc-900/50 border border-white/5 rounded-xl overflow-hidden p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">Summary</h2>
              <StatusPill tone={conversation.status === "resolved" ? "ok" : "warn"}>
                {conversation.status}
              </StatusPill>
            </div>
            <p className="text-sm text-zinc-400 mb-6">{conversation.resolution}</p>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-black rounded-lg border border-white/5">
                <div className="text-xs text-zinc-500 mb-1">Клиент</div>
                <div className="text-sm font-medium text-zinc-200">{conversation.customer}</div>
              </div>
              <div className="p-3 bg-black rounded-lg border border-white/5">
                <div className="text-xs text-zinc-500 mb-1">Latency</div>
                <div className="text-sm font-mono text-zinc-200">{conversation.latency}</div>
              </div>
              <div className="p-3 bg-black rounded-lg border border-white/5">
                <div className="text-xs text-zinc-500 mb-1">Обновлён</div>
                <div className="text-sm text-zinc-200">{conversation.updatedAt}</div>
              </div>
              {conversation.handoffReason ? (
                <div className="p-3 bg-black rounded-lg border border-white/5">
                  <div className="text-xs text-zinc-500 mb-1">Handoff reason</div>
                  <div className="text-sm text-zinc-200">{conversation.handoffReason}</div>
                </div>
              ) : null}
            </div>
          </article>

          {/* Tools Card */}
          <article className="bg-zinc-900/50 border border-white/5 rounded-xl overflow-hidden p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Tools</h2>
            <div className="space-y-3">
              {conversation.tools.map((tool) => (
                <div
                  key={tool.name}
                  className="flex items-center justify-between gap-4 p-4 rounded-lg bg-black border border-white/5"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <Wrench className="w-4 h-4 text-zinc-500" />
                      <h3 className="text-sm font-medium text-white">{tool.name}</h3>
                    </div>
                    <p className="text-xs text-zinc-500 mt-1 ml-6">{tool.latency}</p>
                  </div>
                  <StatusPill tone={toolTone(tool.status)}>{tool.status}</StatusPill>
                </div>
              ))}
            </div>
          </article>
        </div>

        {/* Operator Console */}
        <OperatorConsole
          conversationId={conversation.id}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          messages={conversation.messages as any}
          status={conversation.status}
        />
      </div>
    </DashboardShell>
  );
}
