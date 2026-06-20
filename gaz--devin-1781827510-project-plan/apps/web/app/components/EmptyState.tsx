import Link from "next/link";
import { Plus } from "lucide-react";

type EmptyStateProps = {
  title: string;
  description: string;
  actionHref?: string;
  actionLabel?: string;
};

export function EmptyState({ title, description, actionHref, actionLabel }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center text-center p-12 bg-zinc-900/20 rounded-xl border border-dashed border-white/10">
      <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mb-4">
        <Plus className="w-6 h-6 text-zinc-500" />
      </div>
      <h3 className="text-lg font-medium text-white mb-2">{title}</h3>
      <p className="text-sm text-zinc-400 max-w-sm mb-6">{description}</p>
      {actionHref && actionLabel ? (
        <Link
          href={actionHref}
          className="bg-white text-black hover:bg-zinc-200 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          {actionLabel}
        </Link>
      ) : null}
    </div>
  );
}
