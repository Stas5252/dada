import type { ApiResult } from "../../lib/mvp-data";

type ResultNoticeProps<T> = {
  result: ApiResult<T>;
};

export function ResultNotice<T>({ result }: ResultNoticeProps<T>) {
  if (result.state === "live") {
    return null;
  }

  const label = {
    empty: "Empty state",
    error: "API fallback",
    mock: "Mock data",
  }[result.state];
  const toneClass =
    result.state === "error"
      ? "border-red-500/20 bg-red-500/10 text-red-300"
      : "border-amber-500/20 bg-amber-500/10 text-amber-200";

  return (
    <div className={`rounded-lg border px-4 py-3 text-sm ${toneClass}`} role="status">
      <strong className="font-semibold text-white">{label}:</strong>{" "}
      {result.message ?? `Нет данных из ${result.path}.`}
    </div>
  );
}
