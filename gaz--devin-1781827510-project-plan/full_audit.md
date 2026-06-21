<USER_REQUEST>
нужно крч все пофиксить что не так вот это еще раз все изучи и давай уже проект до конца доделаем:# Полный Аудит CallForce — Сравнение с Конкурентами и План Исправлений

## Конкуренты, с которыми сравниваем

| Платформа | Что делает | Ключевые фичи |
|-----------|-----------|----------------|
| **Vapi.ai** | Voice AI Agents | Real-time voice (WebRTC/SIP), multi-LLM routing, tool calling, STT/TTS swap, аналитика звонков, webhooks |
| **Bland.ai** | AI Phone Calls | Исходящие/входящие звонки, Pathway (визуальный конструктор диалогов), SMS, transfer to human, CRM интеграции |
| **Voiceflow** | Conversational AI Builder | Визуальный drag-and-drop конструктор, RAG из коробки, multi-channel (voice + chat), API интеграции, аналитика |

---

## Текущее Состояние CallForce

### ✅ Что уже работает (хорошо)
1. **Auth**: Регистрация, логин, JWT access+refresh tokens, MFA (TOTP + recovery codes), email verification, password reset
2. **RBAC**: Роли owner/admin/agent/viewer с проверкой прав
3. **Agents CRUD**: Создание/редактирование/удаление агентов с кастомным промптом
4. **Knowledge Base**: Загрузка документов (text, pdf, url), парсинг, RAG через Qdrant
5. **Chat**: Text-based диалоги через Test Console с сохранением в БД
6. **LLM Router**: Маршрутизация между OpenAI / vLLM / Mock с tool calling
7. **Voice Pipeline**: STT (Whisper) → LLM → TTS (OpenAI) через REST
8. **Дизайн**: Glassmorphism dark theme, анимации, единый стиль
9. **Rate Limiting**: SlowAPI на кри
<truncated 12708 bytes>
ARNING]
> **Текущий бекенд работает на `memory` store.** Каждый перезапуск сервера = потеря всех данных. Это ПЕРВОЕ что нужно починить. Миграция на SQLite занимает ~30 минут.

## Verification Plan

### Automated Tests
```bash
# Backend unit tests
cd apps/api && python -m pytest tests/ -v

# Frontend type check
cd apps/web && npx tsc --noEmit
```

### Manual Verification
- E2E flow: Register → Create Agent → Chat → Voice → Analytics
- Browser subagent для автоматического тестирования каждой страницы
- Проверка security: попытка доступа без токена, SQL injection, XSS

</USER_REQUEST>
<ADDITIONAL_METADATA>
The current local time is: 2026-06-20T05:03:49+04:00.

The user's current state is as follows:
Other open documents:
- c:\Users\пп\Desktop\проект\gaz--devin-1781827510-project-plan\apps\api\app\rag.py (LANGUAGE_PYTHON)
- c:\Users\пп\Desktop\проект\gaz--devin-1781827510-project-plan\apps\web\app\components\KnowledgeSourceForm.tsx (LANGUAGE_TSX)
- c:\Users\пп\Desktop\проект\gaz--devin-1781827510-project-plan\apps\web\app\dashboard\page.tsx (LANGUAGE_TSX)
- c:\Users\пп\Desktop\проект\gaz--devin-1781827510-project-plan\apps\api\app\store.py (LANGUAGE_PYTHON)
- c:\Users\пп\Desktop\проект\gaz--devin-1781827510-project-plan\.env.example (LANGUAGE_UNSPECIFIED)
Browser State:
  Page 7A8D3597188BEC05C0BAAF05F6DC988A (CallForce — AI-агенты для звонков и чатов) - http://localhost:3000/dashboard [ACTIVE]
    Viewport: 1920x953, Page Height: 1277
</ADDITIONAL_METADATA>
<USER_SETTINGS_CHANGE>
The user changed setting `Model Selection` from Claude Opus 4.6 (Thinking) to Gemini 3.5 Flash (High). No need to comment on this change if the user doesn't ask about it. If reporting what model you are, please use a human readable name instead of the exact string.
</USER_SETTINGS_CHANGE>