type StatusTone = "ok" | "warn" | "danger" | "neutral";

type StatusPillProps = {
  children: React.ReactNode;
  tone: StatusTone;
};

const toneStyles: Record<StatusTone, string> = {
  ok: "bg-emerald-500/10 text-emerald-400 border-transparent",
  warn: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  danger: "bg-red-500/10 text-red-500 border-red-500/20",
  neutral: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
};

export function StatusPill({ children, tone }: StatusPillProps) {
  return (
    <span
      className={`inline-flex items-center justify-center px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider rounded-full border ${toneStyles[tone]}`}
    >
      {children}
    </span>
  );
}
