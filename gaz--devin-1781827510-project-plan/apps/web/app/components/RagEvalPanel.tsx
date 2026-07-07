"use client";

import { useState, useTransition } from "react";
import { AlertTriangle, CheckCircle2, FlaskConical, Play, XCircle } from "lucide-react";
import { runRagEvalAction, type RagEvalActionResult } from "../actions";

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function statusClass(status: "failed" | "passed") {
  return status === "passed"
    ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-200"
    : "border-red-500/20 bg-red-500/10 text-red-200";
}

export function RagEvalPanel({ defaultSourceTitle = "" }: { defaultSourceTitle?: string }) {
  const [result, setResult] = useState<RagEvalActionResult | null>(null);
  const [isPending, startTransition] = useTransition();

  return (
    <section className="bg-zinc-900/50 border border-white/5 rounded-xl overflow-hidden">
      <div className="border-b border-white/5 p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-300">
              <FlaskConical className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">RAG quality eval</h2>
              <div className="mt-1 text-sm text-zinc-400">Golden answer, citation and no-answer gate.</div>
            </div>
          </div>
          {result?.state === "live" && (
            <span
              data-testid="rag-eval-status"
              className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium ${statusClass(result.data.status)}`}
            >
              {result.data.status === "passed" ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
              {result.data.status}
            </span>
          )}
        </div>
      </div>

      <form
        action={(formData) => {
          startTransition(async () => {
            setResult(await runRagEvalAction(formData));
          });
        }}
        className="grid gap-5 p-6 lg:grid-cols-[1fr_0.9fr]"
      >
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-1.5">
              <span className="text-sm font-medium text-zinc-300">Case name</span>
              <input
                className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white outline-none transition-colors placeholder:text-zinc-600 focus:border-emerald-500"
                defaultValue="Golden answer"
                name="case_name"
              />
            </label>
            <label className="space-y-1.5">
              <span className="text-sm font-medium text-zinc-300">Expected source title</span>
              <input
                className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white outline-none transition-colors placeholder:text-zinc-600 focus:border-emerald-500"
                defaultValue={defaultSourceTitle}
                name="expected_source_titles"
                placeholder="Delivery FAQ"
              />
            </label>
          </div>

          <label className="space-y-1.5 block">
            <span className="text-sm font-medium text-zinc-300">Golden query</span>
            <input
              className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white outline-none transition-colors placeholder:text-zinc-600 focus:border-emerald-500"
              data-testid="rag-eval-query"
              name="query"
              placeholder="How long does delivery take?"
              required
            />
          </label>

          <label className="space-y-1.5 block">
            <span className="text-sm font-medium text-zinc-300">Expected answer terms</span>
            <textarea
              className="min-h-20 w-full resize-y rounded-lg border border-white/10 bg-black px-4 py-3 text-sm leading-6 text-white outline-none transition-colors placeholder:text-zinc-600 focus:border-emerald-500"
              data-testid="rag-eval-terms"
              name="expected_answer_terms"
              placeholder="45 minutes"
            />
          </label>

          <label className="space-y-1.5 block">
            <span className="text-sm font-medium text-zinc-300">No-answer query</span>
            <input
              className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white outline-none transition-colors placeholder:text-zinc-600 focus:border-emerald-500"
              data-testid="rag-eval-negative-query"
              name="negative_query"
              placeholder="Do you repair laptops?"
            />
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-1.5">
              <span className="text-sm font-medium text-zinc-300">Required pass rate</span>
              <input
                className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white outline-none transition-colors focus:border-emerald-500"
                defaultValue="1"
                max="1"
                min="0"
                name="required_pass_rate"
                step="0.05"
                type="number"
              />
            </label>
            <label className="space-y-1.5">
              <span className="text-sm font-medium text-zinc-300">Min relevance</span>
              <input
                className="w-full rounded-lg border border-white/10 bg-black px-4 py-2.5 text-sm text-white outline-none transition-colors focus:border-emerald-500"
                defaultValue="0.2"
                max="1"
                min="0"
                name="min_relevance_score"
                step="0.05"
                type="number"
              />
            </label>
          </div>

          <button
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-2.5 text-sm font-medium text-black transition-colors hover:bg-zinc-200 disabled:bg-white/10 disabled:text-zinc-500"
            data-testid="rag-eval-run"
            disabled={isPending}
            type="submit"
          >
            <Play className="h-4 w-4" />
            {isPending ? "Running" : "Run eval"}
          </button>
        </div>

        <div className="rounded-lg border border-white/5 bg-black p-4">
          {result?.state === "error" && (
            <div className="flex items-start gap-2 text-sm text-red-200" data-testid="rag-eval-error">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              {result.message}
            </div>
          )}

          {result?.state === "live" ? (
            <div className="space-y-4" data-testid="rag-eval-result">
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <div className="text-xs text-zinc-500">Pass rate</div>
                  <div className="mt-1 text-xl font-semibold text-white">{formatPercent(result.data.pass_rate)}</div>
                </div>
                <div>
                  <div className="text-xs text-zinc-500">Passed</div>
                  <div className="mt-1 text-xl font-semibold text-white">{result.data.passed_cases}</div>
                </div>
                <div>
                  <div className="text-xs text-zinc-500">Failed</div>
                  <div className="mt-1 text-xl font-semibold text-white">{result.data.failed_cases}</div>
                </div>
              </div>

              <div className="divide-y divide-white/5 border-t border-white/5">
                {result.data.results.map((item) => (
                  <div key={`${item.name}-${item.query}`} className="py-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-sm font-medium text-white">{item.name}</div>
                        <div className="mt-1 text-xs text-zinc-500">{item.query}</div>
                      </div>
                      <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${statusClass(item.status)}`}>
                        {item.status}
                      </span>
                    </div>
                    <div className="mt-3 grid gap-2 text-xs text-zinc-400">
                      <div>Sources: {item.citation_titles.length ? item.citation_titles.join(", ") : "none"}</div>
                      <div>Matched terms: {item.matched_expected_terms.length ? item.matched_expected_terms.join(", ") : "none"}</div>
                      {item.failures.length > 0 && (
                        <div className="text-red-300">Failures: {item.failures.join(", ")}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            !result && (
              <div className="flex min-h-48 items-center justify-center text-center text-sm text-zinc-500">
                No eval run yet.
              </div>
            )
          )}
        </div>
      </form>
    </section>
  );
}
