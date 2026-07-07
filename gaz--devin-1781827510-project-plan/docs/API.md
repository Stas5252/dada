# API.md — CallForce REST API

## Аутентификация

Все защищённые эндпоинты требуют `Authorization: Bearer <token>`.

### `POST /api/v1/auth/register`
Регистрация нового тенанта.
```json
{
  "company_name": "My Company",
  "owner_email": "owner@example.com",
  "owner_name": "Иван Иванов",
  "password": "secure-password"
}
```

### `POST /api/v1/auth/login`
Вход и получение access/refresh токенов.

### `POST /api/v1/auth/refresh`
Обновление access-токена по refresh-токену.

---

## Агенты

### `GET /api/v1/agents`
Список агентов тенанта.

### `POST /api/v1/agents`
Создание агента.
```json
{
  "name": "Поддержка клиентов",
  "prompt": "Ты AI-помощник стоматологической клиники...",
  "channel": "telegram",
  "model_name": "gpt-4o-mini",
  "enabled_tools": ["capture_lead", "create_crm_deal"]
}
```

### `GET /api/v1/agent-templates`
Список шаблонов агентов (салон, ресторан, клиника и т.д.).

### `POST /api/v1/agents/from-template/{template_id}`
Создание агента из шаблона.

---

## Диалоги

### `GET /api/v1/conversations`
Список диалогов тенанта.

### `POST /api/v1/conversations/{id}/messages`
Отправка сообщения.

---

## CRM

### `GET /api/v1/crm/leads`
Список лидов.

### `POST /api/v1/crm/leads`
Создание лида.

### `GET /api/v1/crm/deals`
Список сделок.

### `POST /api/v1/crm/deals`
Создание сделки.

---

## Голос

### `POST /api/v1/voice/sessions`
Начать голосовую сессию.

### `POST /api/v1/voice/preview-turn`
Text-to-voice preview (для тестирования).

### `WS /api/v1/voice/ws/{session_id}`
WebSocket для full-duplex голоса.

---

## База знаний (RAG)

### `GET /api/v1/knowledge/sources`
Список источников знаний.

### `POST /api/v1/knowledge/sources`
Загрузка источника (PDF/DOCX/URL/текст).

---

## Система

### `GET /api/v1/system/health`
Health check.

### `GET /api/v1/system/readiness`
Матрица готовности всех провайдеров.

---

## Webhooks

### `POST /api/v1/webhooks/telegram/{agent_id}`
Вебхук Telegram.

### `POST /api/v1/webhooks/vk/{agent_id}`
Вебхук VK.

### `POST /api/v1/webhooks/whatsapp/{agent_id}`
Вебхук WhatsApp.

### `POST /api/v1/webhooks/yookassa`
Вебхук YooKassa.

### `POST /api/v1/webhooks/twilio/voice`
Вебхук Twilio Voice.
