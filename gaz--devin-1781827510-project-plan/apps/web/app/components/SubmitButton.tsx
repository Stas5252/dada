"use client";

import { useFormStatus } from "react-dom";
import { Loader2 } from "lucide-react";
import { ButtonHTMLAttributes, ReactNode } from "react";

interface SubmitButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  pendingText?: ReactNode;
  className?: string;
}

export function SubmitButton({ children, pendingText, ...props }: SubmitButtonProps) {
  const { pending } = useFormStatus();

  return (
    <button
      type="submit"
      disabled={pending || props.disabled}
      className={`relative flex items-center justify-center gap-2 transition-all ${props.className || ""}`}
      {...props}
    >
      {pending && <Loader2 className="h-4 w-4 animate-spin" />}
      <span className={pending ? "opacity-70" : ""}>
        {pending && pendingText ? pendingText : children}
      </span>
    </button>
  );
}
