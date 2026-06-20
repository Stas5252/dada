import { ActionNotice } from "../components/ActionNotice";
import { DashboardShell } from "../components/DashboardShell";
import { EmptyState } from "../components/EmptyState";
import { ResultNotice } from "../components/ResultNotice";
import { StatusPill } from "../components/StatusPill";
import { reingestKnowledgeSourceAction } from "../actions";
import { getKnowledgeIngestionJobs, getKnowledgeSources } from "../../lib/mvp-data";
import {
  CheckCircle2,
  Clock3,
  Database,
  FileText,
  Globe,
  Link as LinkIcon,
  RefreshCw,
  RotateCw,
} from "lucide-react";
import { KnowledgeSourceForm } from "../components/KnowledgeSourceForm";

type KnowledgePageProps = {
  searchParams?: Promise<{
    notice?: string;
  }>;
};

function sourceTone(status: "failed" | "indexed" | "needs_review" | "pending" | "processing") {
  if (status === "indexed") return "ok";
  if (status === "failed" || status === "needs_review") return "danger";
  return "warn";
}

function jobTone(status: "completed" | "failed" | "queued" | "running") {
  if (status === "completed") return "ok";
  if (status === "failed") return "danger";
  return "warn";
}

export default async function KnowledgePage({ searchParams }: KnowledgePageProps) {
  const [sourcesResult, jobsResult] = await Promise.all([
    getKnowledgeSources(),
    getKnowledgeIngestionJobs(),
  ]);
  const notice = (await searchParams)?.notice;
  const failedJobs = jobsResult.data.filter((job) => job.status === "failed").length;
  const processingJobs = jobsResult.data.filter(
    (job) => job.status === "queued" || job.status === "running",
  ).length;
  const sourceNames = new Map(sourcesResult.data.map((source) => [source.id, source.name]));
  const latestJobs = [...jobsResult.data].slice(0, 6);

  return (
    <DashboardShell
      activePath="/knowledge"
      eyebrow="База Знаний"
      title="Источники знаний"
      description="Загрузите данные для RAG (Retrieval-Augmented Generation), чтобы агенты могли отвечать по вашей базе."
    >
      <div className="space-y-6">
        <ActionNotice notice={notice} />
        <ResultNotice result={sourcesResult} />
        <ResultNotice result={jobsResult} />

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Upload Form */}
          <article className="lg:col-span-2 bg-zinc-900/50 border border-white/5 rounded-xl overflow-hidden p-6">
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-white mb-2">Загрузить данные</h2>
              <p className="text-sm text-zinc-400">Форма подготавливает payload для RAG pipeline: upload → chunking → embeddings → index.</p>
            </div>
            <KnowledgeSourceForm />
          </article>

          {/* Stats Snapshot */}
          <article className="bg-zinc-900/50 border border-white/5 rounded-xl overflow-hidden p-6">
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-white mb-2">Статистика RAG</h2>
              <p className="text-sm text-zinc-400">Покрытие базы знаний.</p>
            </div>

            <div className="space-y-4">
              <div className="bg-black border border-white/5 rounded-lg p-4 flex items-center justify-between">
                <div className="flex items-center gap-3 text-zinc-300">
                  <FileText className="w-5 h-5 text-zinc-500" />
                  <span className="text-sm font-medium">Документов</span>
                </div>
                <span className="text-xl font-bold text-white">
                  {sourcesResult.data.reduce((total, source) => total + source.documents, 0)}
                </span>
              </div>

              <div className="bg-black border border-white/5 rounded-lg p-4 flex items-center justify-between">
                <div className="flex items-center gap-3 text-zinc-300">
                  <Database className="w-5 h-5 text-emerald-500" />
                  <span className="text-sm font-medium">Покрытие</span>
                </div>
                <span className="text-xl font-bold text-white">
                  {sourcesResult.data.length > 0
                    ? `${Math.round(
                        sourcesResult.data.reduce((total, source) => total + source.coverageScore, 0) /
                          sourcesResult.data.length,
                      )}%`
                    : "—"}
                </span>
              </div>

              <div className="bg-black border border-white/5 rounded-lg p-4 flex items-center justify-between">
                <div className="flex items-center gap-3 text-zinc-300">
                  <RefreshCw className="w-5 h-5 text-amber-500" />
                  <span className="text-sm font-medium">В обработке</span>
                </div>
                <span className="text-xl font-bold text-white">{processingJobs}</span>
              </div>

              <div className="bg-black border border-white/5 rounded-lg p-4 flex items-center justify-between">
                <div className="flex items-center gap-3 text-zinc-300">
                  <Clock3 className="w-5 h-5 text-red-500" />
                  <span className="text-sm font-medium">Ошибки ingestion</span>
                </div>
                <span className="text-xl font-bold text-white">{failedJobs}</span>
              </div>
            </div>
          </article>
        </div>

        <section className="bg-zinc-900/50 border border-white/5 rounded-xl overflow-hidden">
          <div className="p-6 border-b border-white/5 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">Ingestion pipeline</h2>
              <p className="text-sm text-zinc-400">
                Последние задачи индексации: chunking, embeddings и запись в Qdrant-ready collection.
              </p>
            </div>
            <StatusPill tone={failedJobs > 0 ? "danger" : processingJobs > 0 ? "warn" : "ok"}>
              {failedJobs > 0 ? "Needs review" : processingJobs > 0 ? "Processing" : "Healthy"}
            </StatusPill>
          </div>

          {latestJobs.length > 0 ? (
            <div className="divide-y divide-white/5">
              {latestJobs.map((job) => (
                <div
                  key={job.id}
                  className="grid gap-4 p-5 sm:grid-cols-[1.3fr_0.8fr_auto] sm:items-center"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      {job.status === "completed" ? (
                        <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-emerald-500" />
                      ) : (
                        <RefreshCw className="h-4 w-4 flex-shrink-0 text-amber-500" />
                      )}
                      <div className="truncate text-sm font-medium text-white">
                        {sourceNames.get(job.sourceId) ?? job.sourceId}
                      </div>
                    </div>
                    <div className="mt-1 truncate text-xs text-zinc-500">
                      {job.collection} / {job.backend}
                    </div>
                    {job.errorMessage && (
                      <div className="mt-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-300">
                        {job.errorMessage}
                      </div>
                    )}
                  </div>
                  <div className="text-sm text-zinc-400">
                    {job.chunkCount} chunks · {job.updatedAt}
                  </div>
                  <StatusPill tone={jobTone(job.status)}>{job.status}</StatusPill>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-6 text-sm text-zinc-500">
              Задач ingestion пока нет. Загрузите первый источник, чтобы запустить pipeline.
            </div>
          )}
        </section>

        {/* Sources Table */}
        <section className="bg-zinc-900/50 border border-white/5 rounded-xl overflow-hidden">
          <div className="p-6 border-b border-white/5">
            <h2 className="text-lg font-semibold text-white">Текущие источники</h2>
            <p className="text-sm text-zinc-400">Документы, статус синхронизации и оценка покрытия для RAG.</p>
          </div>

          {sourcesResult.data.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-white/5 bg-zinc-950/50">
                    <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Название</th>
                    <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Тип</th>
                    <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Статус</th>
                    <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Docs</th>
                    <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Coverage</th>
                    <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Updated</th>
                    <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {sourcesResult.data.map((source) => (
                    <tr key={source.id} className="hover:bg-white/[0.04] transition-colors group cursor-pointer">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-300 font-medium">
                        {source.name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2 text-sm text-zinc-400">
                          {source.type === "url" ? <Globe className="w-4 h-4" /> : source.type === "integration" ? <LinkIcon className="w-4 h-4" /> : <FileText className="w-4 h-4" />}
                          <span className="capitalize">{source.type}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <StatusPill tone={sourceTone(source.syncStatus)}>{source.syncStatus}</StatusPill>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-400">
                        {source.documents}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-emerald-500"
                              style={{ width: `${source.coverageScore}%` }}
                            />
                          </div>
                          <span className="text-xs text-zinc-400 font-mono">{source.coverageScore}%</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-500">
                        {source.updatedAt}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <form action={reingestKnowledgeSourceAction}>
                          <input name="source_id" type="hidden" value={source.id} />
                          <button
                            type="submit"
                            className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-1.5 text-xs font-medium text-zinc-300 transition-colors hover:bg-white/5 hover:text-white"
                          >
                            <RotateCw className="h-3.5 w-3.5" />
                            Re-index
                          </button>
                        </form>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              description="Загрузите текст, URL или подключите интеграцию, чтобы начать индексацию."
              title="Источников знаний пока нет"
            />
          )}
        </section>
      </div>
    </DashboardShell>
  );
}
