"use client";

import { useState } from "react";
import { Upload } from "lucide-react";
import { createKnowledgeSourceAction } from "../actions";
import { SubmitButton } from "./SubmitButton";

export function KnowledgeSourceForm() {
  const [sourceType, setSourceType] = useState("manual");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [fileName, setFileName] = useState("");

  return (
    <form
      action={(formData) => {
        setIsSubmitting(true);
        createKnowledgeSourceAction(formData).finally(() => setIsSubmitting(false));
      }}
      className="space-y-4"
    >
      <div>
        <label className="block text-sm font-medium text-zinc-300 mb-1.5">
          Тип источника
        </label>
        <select
          value={sourceType}
          onChange={(e) => setSourceType(e.target.value)}
          name="source_type"
          className="w-full bg-black border border-white/10 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-emerald-500 transition-colors appearance-none"
        >
          <option value="manual">Ввод текста / FAQ</option>
          <option value="file">Загрузка файла (.txt, .md)</option>
          <option value="url">URL / страница сайта</option>
        </select>
      </div>

      {sourceType === "file" && (
        <div className="border-2 border-dashed border-white/10 rounded-lg p-8 text-center hover:border-emerald-500/50 transition-colors">
          <input
            type="file"
            name="file"
            id="file-upload"
            accept=".txt,.md,.csv"
            className="hidden"
            required
            onChange={(e) => {
              setFileName(e.target.files?.[0]?.name ?? "");
            }}
          />
          <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center justify-center space-y-2">
            <Upload className="w-8 h-8 text-zinc-500 mb-2" />
            <span className="text-sm font-medium text-emerald-500 hover:text-emerald-400">Выберите файл</span>
            <span className="text-xs text-zinc-500">
              {fileName || "UTF-8 файл .txt, .md или .csv"}
            </span>
          </label>
        </div>
      )}

      {sourceType !== "file" && (
        <>
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-1.5">
              {sourceType === "url" ? "URL или название страницы" : "Название источника"}
            </label>
            <input
              name="title"
              placeholder={
                sourceType === "url"
                  ? "https://example.com/faq"
                  : "Например, Меню и FAQ доставки"
              }
              required
              className="w-full bg-black border border-white/10 rounded-lg px-4 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors"
            />
          </div>

          {sourceType !== "url" && (
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1.5">
                Содержимое
              </label>
              <textarea
                name="content"
                placeholder="Доставка занимает 45-60 минут. Бесплатная доставка от 1000 рублей. Оплата доступна картой, наличными или по ссылке."
                required
                rows={6}
                className="w-full bg-black border border-white/10 rounded-lg px-4 py-3 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors resize-y"
              />
            </div>
          )}
        </>
      )}

      <div className="flex gap-3 pt-2">
        <SubmitButton
          className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-black transition-colors hover:bg-zinc-200 disabled:bg-white/10 disabled:text-zinc-500"
        >
          {isSubmitting ? "Обработка..." : "Загрузить"}
        </SubmitButton>
      </div>
    </form>
  );
}
