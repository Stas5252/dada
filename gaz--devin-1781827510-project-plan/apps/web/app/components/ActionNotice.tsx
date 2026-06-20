"use client";

import { useEffect } from "react";
import { toast } from "sonner";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

const notices: Record<string, { tone: "Danger" | "Info"; text: string; title: string }> = {
  "auth-invalid": {
    tone: "Danger",
    title: "Auth error",
    text: "Заполните все обязательные поля.",
  },
  "auth-error": {
    tone: "Danger",
    title: "Auth failed",
    text: "Неверные учетные данные или произошла ошибка.",
  },
  "tenant-exists": {
    tone: "Danger",
    title: "Registration failed",
    text: "Пользователь с таким email уже существует.",
  },
  "password-reset": {
    tone: "Info",
    title: "Success",
    text: "Пароль успешно обновлён.",
  },
  "agent-created": {
    tone: "Info",
    title: "Agent saved",
    text: "Draft agent создан через live Core API.",
  },
  "agent-error": {
    tone: "Danger",
    title: "Agent error",
    text: "Core API не сохранил агента.",
  },
  "agent-not-found": {
    tone: "Danger",
    title: "Agent not found",
    text: "Агент не найден в текущем tenant.",
  },
  "agent-published": {
    tone: "Info",
    title: "Agent published",
    text: "Агент опубликован через live Core API.",
  },
  "agent-publish-error": {
    tone: "Danger",
    title: "Publish error",
    text: "Core API не опубликовал агента.",
  },
  "agent-updated": {
    tone: "Info",
    title: "Agent updated",
    text: "Конфигурация агента обновлена; изменение prompt или channel возвращает агента в draft.",
  },
  "agent-update-error": {
    tone: "Danger",
    title: "Agent update error",
    text: "Core API не обновил агента.",
  },
  "agent-invalid": {
    tone: "Danger",
    title: "Agent form",
    text: "Заполните название и prompt не короче 10 символов.",
  },
  "chat-created": {
    tone: "Info",
    title: "Test chat",
    text: "Тестовый диалог создан через live Core API.",
  },
  "chat-error": {
    tone: "Danger",
    title: "Test chat error",
    text: "Core API не создал тестовый диалог.",
  },
  "chat-invalid": {
    tone: "Danger",
    title: "Test chat form",
    text: "Выберите агента и введите сообщение.",
  },
  "voice-preview-created": {
    tone: "Info",
    title: "Voice preview",
    text: "Голосовой preview создан, transcript сохранен через live Core API.",
  },
  "voice-preview-error": {
    tone: "Danger",
    title: "Voice preview error",
    text: "Core API не создал голосовой preview.",
  },
  "voice-preview-invalid": {
    tone: "Danger",
    title: "Voice preview form",
    text: "Выберите агента и введите фразу клиента.",
  },
  "knowledge-created": {
    tone: "Info",
    title: "Knowledge saved",
    text: "Source загружен и отправлен в ingestion.",
  },
  "knowledge-error": {
    tone: "Danger",
    title: "Knowledge error",
    text: "Core API не сохранил source.",
  },
  "knowledge-invalid-file": {
    tone: "Danger",
    title: "Knowledge file",
    text: "Выберите непустой UTF-8 файл .txt, .md или .csv.",
  },
  "knowledge-invalid": {
    tone: "Danger",
    title: "Knowledge form",
    text: "Заполните название и content источника.",
  },
  "knowledge-reingested": {
    tone: "Info",
    title: "Knowledge ingestion",
    text: "Источник отправлен на повторную индексацию через live Core API.",
  },
  "knowledge-reingest-error": {
    tone: "Danger",
    title: "Knowledge ingestion",
    text: "Core API не запустил повторную индексацию источника.",
  },
  "settings-updated": {
    tone: "Info",
    title: "Settings saved",
    text: "Настройки каналов и интеграций сохранены.",
  },
  "settings-error": {
    tone: "Danger",
    title: "Settings error",
    text: "Не удалось сохранить настройки интеграций.",
  },
  "call-initiated": {
    tone: "Info",
    title: "Call initiated",
    text: "Исходящий звонок запущен! Проверьте лог или телефон.",
  },
  "call-error": {
    tone: "Danger",
    title: "Call error",
    text: "Не удалось запустить исходящий звонок. Проверьте настройки или API ключ.",
  },
};

export function ActionNotice({ notice }: { notice?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (!notice) return;

    const config = notices[notice];
    if (config) {
      if (config.tone === "Danger") {
        toast.error(config.title, { description: config.text });
      } else {
        toast.success(config.title, { description: config.text });
      }
    } else {
      // Fallback for custom notices
      if (notice.includes("error") || notice.includes("invalid")) {
        toast.error("Ошибка", { description: "Произошла ошибка при выполнении операции." });
      } else {
        toast.success("Успешно", { description: "Операция выполнена успешно." });
      }
    }

    // Remove notice from URL
    const params = new URLSearchParams(searchParams.toString());
    params.delete("notice");
    router.replace(`${pathname}?${params.toString()}`);
  }, [notice, pathname, router, searchParams]);

  return null;
}
