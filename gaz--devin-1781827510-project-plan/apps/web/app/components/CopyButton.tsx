"use client";

import { useState } from "react";
import { Copy, Check } from "lucide-react";

interface CopyButtonProps {
  text: string;
  className?: string;
}

export function CopyButton({ text, className = "" }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy text: ", err);
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={`p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-white/5 transition-all flex items-center justify-center gap-1.5 ${className}`}
      title="Копировать в буфер"
    >
      {copied ? (
        <>
          <Check className="w-4 h-4 text-emerald-500" />
          <span className="text-xs text-emerald-500 font-medium">Скопировано!</span>
        </>
      ) : (
        <>
          <Copy className="w-4 h-4" />
        </>
      )}
    </button>
  );
}
