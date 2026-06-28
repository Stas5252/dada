"use client";

import { useFormStatus } from "react-dom";
import { triggerOutboundCallAction } from "../actions";

function SubmitButton() {
  const { pending } = useFormStatus();
  
  return (
    <button
      type="submit"
      disabled={pending}
      className="bg-white text-black text-sm font-medium px-6 py-2.5 rounded hover:bg-zinc-200 transition-colors whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {pending ? "Отправка..." : "Позвонить мне"}
    </button>
  );
}

export function CallTestForm() {
  return (
    <form action={triggerOutboundCallAction} className="flex flex-col sm:flex-row gap-3">
      <input name="return_to" type="hidden" value="/" />
      <input
        type="tel"
        name="to_number"
        placeholder="+7 (999) 123-45-67"
        pattern="^\+7\s?\(?\d{3}\)?\s?\d{3}-?\d{2}-?\d{2}$"
        title="Формат: +7 (999) 123-45-67"
        required
        className="flex-1 rounded border border-white/20 bg-black px-4 py-2.5 text-sm text-white placeholder-zinc-600 outline-none focus:border-white transition-colors"
      />
      <SubmitButton />
    </form>
  );
}
