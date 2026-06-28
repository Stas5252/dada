import Link from "next/link";
import { notFound } from "next/navigation";
import { DashboardShell } from "../../components/DashboardShell";
import { StatusPill } from "../../components/StatusPill";
import { ActionNotice } from "../../components/ActionNotice";
import { ResultNotice } from "../../components/ResultNotice";
import { reingestKnowledgeSourceAction } from "../../actions";
import { getKnowledgeSource, getKnowledgeIngestionJobs } from "../../../lib/mvp-data";
import {
  ArrowLeft,
  FileText,
  Globe,
  Link as LinkIcon,
  RotateCw,
  Database,
  Calendar,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";

type SourceDetailPageProps = {
  params: Promise<{
    id: string;
  }>;
  searchParams?: Promise<{
    notice?: string;
  }>;
};

function sourceTone(status: string) {
  if (status === "indexed") return "ok";
  if (status === "failed" || status === "needs_review") return "danger";
  return "warn";
}

function jobTone(status: string) {
  if (status === "completed") return "ok";
  if (status === "failed") return "danger";
  return "warn";
}

export default async function KnowledgeSourceDetailPage({ params, searchParams }: SourceDetailPageProps) {
  const { id } = await params;
  const resolvedSearchParams = searchParams ? await searchParams : null;
  const notice = resolvedSearchParams?.notice;

  const [sourceResult, jobsResult] = await Promise.all([
    getKnowledgeSource(id),
    getKnowledgeIngestionJobs(),
  ]);

  if (sourceResult.state === "live" && !sourceResult.data) {
    notFound();
  }

  const source = sourceResult.data;
  const jobs = jobsResult.data.filter((job) => job.sourceId === id);
  const latestJobs = [...jobs].slice(0, 5);

  return (
    <DashboardShell
      activePath="/knowledge"
      eyebrow="База Знаний"
      title={source ? source.name : "Детали источника"}
      description="Детальная информация об источнике знаний, сгенерированных чанках и статусе его индексирования."
      actions={
        <Link
          href="/knowledge"
          className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm font-medium text-zinc-300 transition-colors hover:bg-white/10 hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          Назад в базу
        </Link>
      }
    >
      <div className="space-y-6 max-w-5xl">
        <ActionNotice notice={notice} />
        <ResultNotice result={sourceResult} />
        <ResultNotice result={jobsResult} />

        {source && (
          <>
            <div className="grid md:grid-cols-3 gap-6">
              {/* Metadata details card */}
              <article className="md:col-span-2 bg-zinc-900/50 border border-white/5 rounded-xl p-6 space-y-6">
                <div>
                  <h3 className="text-sm font-semibold text-zinc-400 mb-3">Информация об источнике</h3>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div className="bg-black/40 border border-white/5 rounded-lg p-4 flex items-center justify-between">
                      <div className="flex items-center gap-3 text-zinc-300">
                        {source.type === "url" ? (
                          <Globe className="w-5 h-5 text-sky-400" />
                        ) : source.type === "integration" ? (
                          <LinkIcon className="w-5 h-5 text-purple-400" />
                        ) : (
                          <FileText className="w-5 h-5 text-emerald-400" />
                        )}
                        <div>
                          <span className="text-xs text-zinc-500 block">Тип источника</span>
                          <span className="text-sm font-medium capitalize">{source.type}</span>
                        </div>
                      </div>
                    </div>

                    <div className="bg-black/40 border border-white/5 rounded-lg p-4 flex items-center justify-between">
                      <div className="flex items-center gap-3 text-zinc-300">
                        <Database className="w-5 h-5 text-zinc-400" />
                        <div>
                          <span className="text-xs text-zinc-500 block">Качество покрытия</span>
                          <span className="text-sm font-medium font-mono">{source.coverageScore}%</span>
                        </div>
                      </div>
                      <div className="w-12 h-1 bg-white/10 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-emerald-500"
                          style={{ width: `${source.coverageScore}%` }}
                        />
                      </div>
                    </div>

                    <div className="bg-black/40 border border-white/5 rounded-lg p-4 flex items-center justify-between">
                      <div className="flex items-center gap-3 text-zinc-300">
                        <Calendar className="w-5 h-5 text-zinc-400" />
                        <div>
                          <span className="text-xs text-zinc-500 block">Обновлено</span>
                          <span className="text-sm font-medium">{source.updatedAt}</span>
                        </div>
                      </div>
                    </div>

                    <div className="bg-black/40 border border-white/5 rounded-lg p-4 flex items-center justify-between">
                      <div className="flex items-center gap-3 text-zinc-300">
                        <RotateCw className="w-5 h-5 text-amber-500" />
                        <div>
                          <span className="text-xs text-zinc-500 block">Статус синхронизации</span>
                          <div className="mt-0.5">
                            <StatusPill tone={sourceTone(source.syncStatus)}>{source.syncStatus}</StatusPill>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Content preview snippet */}
                {source.content && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold text-zinc-400">Предпросмотр контента базы</h4>
                    <div className="bg-black/60 rounded-xl p-4 border border-white/5 max-h-72 overflow-y-auto text-xs font-mono text-zinc-300 whitespace-pre-wrap leading-relaxed">
                      {source.content}
                    </div>
                  </div>
                )}
              </article>

              {/* Action and Ingestion stats sidebar */}
              <article className="bg-zinc-900/50 border border-white/5 rounded-xl p-6 space-y-6 flex flex-col justify-between">
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-zinc-400">Параметры RAG</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-sm py-1 border-b border-white/5">
                      <span className="text-zinc-500">Документов</span>
                      <span className="text-white font-medium">{source.documents}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm py-1 border-b border-white/5">
                      <span className="text-zinc-500">Количество чанков</span>
                      <span className="text-white font-medium font-mono">{source.chunkCount ?? 0}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm py-1">
                      <span className="text-zinc-500">Идентификатор</span>
                      <span className="text-zinc-400 font-mono text-xs truncate max-w-[120px]" title={source.id}>
                        {source.id}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="pt-6 border-t border-white/5 space-y-3">
                  <form action={reingestKnowledgeSourceAction}>
                    <input name="source_id" type="hidden" value={source.id} />
                    <button
                      type="submit"
                      className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-500"
                    >
                      <RotateCw className="h-4 w-4" />
                      Переиндексировать
                    </button>
                  </form>
                  <p className="text-[10px] text-zinc-500 text-center leading-normal">
                    Запустит повторное разбиение на чанки и обновит векторы в Qdrant.
                  </p>
                </div>
              </article>
            </div>

            {/* Ingestion pipeline logs specific for this source */}
            <section className="bg-zinc-900/50 border border-white/5 rounded-xl overflow-hidden">
              <div className="p-6 border-b border-white/5">
                <h2 className="text-lg font-semibold text-white">Журнал задач индексирования</h2>
                <p className="text-sm text-zinc-400">
                  Последние запуски индексации для текущего источника.
                </p>
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
                          ) : job.status === "failed" ? (
                            <AlertCircle className="h-4 w-4 flex-shrink-0 text-red-500" />
                          ) : (
                            <RefreshCw className="h-4 w-4 flex-shrink-0 text-amber-500 animate-spin" />
                          )}
                          <div className="truncate text-sm font-medium text-white">
                            Задача Ingestion ({job.id.slice(0, 8)}...)
                          </div>
                        </div>
                        <div className="mt-1 truncate text-xs text-zinc-500">
                          Коллекция: {job.collection} / Воркер: {job.backend}
                        </div>
                        {job.errorMessage && (
                          <div className="mt-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-300">
                            {job.errorMessage}
                          </div>
                        )}
                      </div>
                      <div className="text-sm text-zinc-400">
                        {job.chunkCount} чанков · {job.updatedAt}
                      </div>
                      <StatusPill tone={jobTone(job.status)}>{job.status}</StatusPill>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-6 text-sm text-zinc-500">
                  История запусков по данному источнику пуста.
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </DashboardShell>
  );
}
