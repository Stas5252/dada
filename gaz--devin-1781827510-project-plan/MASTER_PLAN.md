# CallForce — Мастер-план: от текущего состояния до production

> Единый документ. Всё что есть, всё что нужно сделать, как именно это сделать, как протестировать.
> Дата: 26 июня 2026. ~~Общая готовность: **~55-60%**~~ (устаревшая оценка).
> **Обновлено 28 июня 2026: ~80-85%** — после глубокого code review выяснилось, что большинство P0/P1 задач уже реализованы в коде.

---

## 1. ИНВЕНТАРИЗАЦИЯ: ЧТО УЖЕ ЕСТЬ

### 1.1 Backend — FastAPI (`apps/api/`)

| Модуль | Файл | LOC | Статус | Что делает |
|--------|-------|-----|--------|-----------|
| Entry point | `main.py` | 161 | ✅ Работает | FastAPI app, CORS, rate limit, secure headers, Sentry, Prometheus, lifespan ARI |
| Settings | `settings.py` | 86 | ✅ Работает | Pydantic settings: DB, Redis, Qdrant, LLM, auth, Twilio, SMTP, Sentry, OTEL |
| Store (InMemory) | `store.py` | 40K | ✅ Работает | Полный InMemory store — tenants, users, agents, knowledge, conversations, orders, billing |
| Store (SQLAlchemy) | `sqlalchemy_store.py` | 74K | ✅ Работает | Полный PostgreSQL store — зеркало InMemory с реальной персистентностью |
| Store Factory | `store_factory.py` | 23 | ✅ Работает | Переключение `STORE_BACKEND=memory|sqlalchemy`, auto-seed demo |
| DB Models | `db_models.py` | 362 | ✅ Работает | 20 SQLAlchemy моделей: tenants, users, memberships, auth_sessions, agents, knowledge, conversations, messages, orders, billing, api_keys, webhooks, test_cases, test_runs |
| Database | `database.py` | ~30 | ✅ Работает | SQLAlchemy engine + session factory |
| Schemas | `schemas.py` | 11K | ✅ Работает | Pydantic schemas для всех сущностей |
| Orchestrator | `orchestrator.py` | 391 | ✅ Работает | Полный dialog pipeline: history → RAG → LLM → tools → guard rails → response |
| LLM Router | `llm_router.py` | 252 | ✅ Работает | OpenAI / vLLM / mock routing, tool calling, auto-strategy |
| RAG | `rag.py` | 247 | ✅ Работает | Chunking, embeddings (OpenAI/local stub), Qdrant upsert/search, citations |
| Security | `security.py` | ~200 | ✅ Работает | JWT HS256, PBKDF2 password hashing, token verification, MFA TOTP |
| RBAC | `rbac.py` | ~70 | ✅ Работает | Role helpers, permission checks |
| Voice Service | `voice_service.py` | 98 | 🟡 Частично | Voice state machine, session management — но только in-memory, нет реального SIP |
| Speech Service | `speech_service.py` | 113 | ✅ Работает | OpenAI Whisper STT + OpenAI TTS, streaming STT/TTS interfaces с mock-реализацией |
| Scenario Engine | `scenario_engine.py` | 136 | 🟡 Частично | Intent matching, pathway interpretation — но нет visual builder UI |
| Billing Service | `billing_service.py` | 110 | 🟡 Частично | Ledger, idempotency, usage charges — `yookassa>=3.0.0` уже в pyproject.toml! |
| Action Engine | `action_engine_executor.py` | ~250 | ✅ Работает | Tool execution: add_to_cart, checkout, confirm_order, escalate_to_human |
| Guard Rails | `guard_rails.py` | ~80 | ✅ Работает | Inbound/outbound message filtering |
| Integration Services | `integration_services.py` | 11K | ✅ Работает | iiko client (auth, menu import, order creation), adapters |
| Telegram Adapter | `channels/telegram_adapter.py` | 171 | ✅ Работает | Parse updates, send messages, set webhook, dedup, markdown retry |
| VK Adapter | `channels/vk_adapter.py` | ~90 | ✅ Работает | VK community webhook, message normalization |
| WhatsApp Adapter | `channels/whatsapp_adapter.py` | ~140 | ✅ Работает | WhatsApp cloud API webhook, message normalization |
| Email Service | `email_service.py` | ~60 | 🟡 Partial | SMTP sender — нет проверенного production setup |
| Audit | `audit.py` | ~100 | ✅ Работает | Audit log creation, tenant/user/event tracking |
| Encryption | `encryption.py` | ~40 | ✅ Работает | Fernet encryption for secrets |
| Parsers | `parsers.py` | ~80 | ✅ Работает | PDF, DOCX, URL парсинг для knowledge base |
| Tracing | `tracing.py` | ~50 | ✅ Работает | OpenTelemetry setup |
| Logging | `logging_setup.py` | ~50 | ✅ Работает | Structured JSON logging |
| Limiter | `limiter.py` | ~20 | ✅ Работает | SlowAPI rate limiter (memory/redis) |
| Asterisk ARI | `asterisk_ari_service.py` | ~180 | 🔴 Skeleton | ARI WebSocket client — структура есть, реального Asterisk нет |
| Twilio Service | `twilio_service.py` | 175 | ✅ Работает | Outbound calls, SMS, TwiML generation, simulation mode — полный код, нужен только account |
| PII Masking | `contracts/masking.py` | 58 | ✅ Работает | Sensitive field masking, cross-tenant redaction — 152-ФЗ compliance |
| Webhook Signing | `contracts/integrations.py` | 119 | ✅ Работает | HMAC-SHA256 webhook signature/verification |
| Demo Data | `demo_data.py` | ~140 | ✅ Работает | Demo tenant, users, agents, knowledge sources, conversations |
| Policy Validator | `policy_validator.py` | ~50 | ✅ Работает | Agent prompt policy validation |
| Service Factory | `service_factory.py` | ~70 | ✅ Работает | Cached adapter factories (VK, WhatsApp) |

### 1.2 API Endpoints (`apps/api/app/api/v1/`)

| Файл | Endpoints | Статус |
|------|-----------|--------|
| `auth.py` | register, login, login/mfa, refresh, logout, me, mfa/setup, mfa/verify, mfa/recovery-codes, mfa/disable, verify-email, request-password-reset, reset-password | ✅ Полный |
| `agents.py` | GET/POST /agents, GET/PATCH /agents/{id}, POST /agents/{id}/publish | ✅ Работает |
| `knowledge.py` | GET/POST sources, POST upload, POST ingest, GET jobs, GET qdrant/contract | ✅ Работает |
| `conversations.py` | GET /conversations, GET /conversations/{id} | ✅ Работает |
| `voice.py` | 701 LOC — sessions, preview-turn, audio STT→LLM→TTS, WebSocket browser streaming, Twilio Media Stream с barge-in, Twilio voice+SMS webhooks, outbound calls | ✅ Работает (REST+WS полные, нужен только Twilio/SIP account) |
| `billing.py` | checkout, usage, plans, invoices, yookassa webhook | 🟡 Partial — структура есть, ЮKassa — stub |
| `analytics.py` | GET reports, dashboard metrics | 🟡 Partial — базовые метрики |
| `integrations.py` | iiko connect/sync/order, webhook management | ✅ iiko работает |
| `telegram.py` | POST webhook/{token}, POST connect | ✅ Работает |
| `vk.py` | POST webhook | ✅ Работает |
| `whatsapp.py` | GET/POST webhook | ✅ Работает |
| `widget.py` | POST /widget/chat/{agent_id} | ✅ Работает |
| `team.py` | invite, list members, update role, remove | ✅ Работает |
| `api_keys.py` | create, list, revoke | ✅ Работает |
| `tenants.py` | GET dashboard, POST settings | ✅ Работает |
| `health.py` | GET /readiness — DB, Redis, Qdrant, LLM, Twilio, STT/TTS status | ✅ Работает |
| `audit.py` | GET audit logs | ✅ Работает |
| `demo.py` | POST demo/request | ✅ Работает |
| `testbed.py` | Test cases CRUD, test runs | ✅ Работает |

### 1.3 Frontend — Next.js (`apps/web/`)

| Страница/Route | Файл | Статус | Что делает |
|----------------|------|--------|-----------|
| Landing `/` | `page.tsx` (666 LOC) | ✅ Готов | Hero, features, integrations, cases, pricing, FAQ, demo request, ROI CTA, footer |
| Login `/login` | `login/page.tsx` | ✅ Работает | Email/password form → JWT cookies |
| Login MFA `/login/mfa` | `login/mfa/page.tsx` | ✅ Работает | TOTP/recovery code |
| Register `/register` | `register/page.tsx` | ✅ Работает | Company + owner registration |
| Forgot Password `/forgot-password` | `forgot-password/page.tsx` | ✅ Работает | Email form |
| Reset Password `/reset-password` | `reset-password/page.tsx` | ✅ Работает | Token + new password |
| Verify Email `/verify-email` | `verify-email/page.tsx` | ✅ Работает | Token verification |
| Dashboard `/dashboard` | `dashboard/page.tsx` | 🟡 Partial | KPIs, readiness, recent conversations — needs real data binding |
| Agents `/agents` | `agents/page.tsx` | ✅ Работает | List, create, edit, publish, test links |
| Agent Detail `/agents/[id]` | `agents/[id]/page.tsx` | ✅ Работает | Edit name/channel/prompt, publish, test |
| New Agent `/agents/new` | `agents/new/page.tsx` | ✅ Работает | Create form with all fields |
| Knowledge `/knowledge` | `knowledge/page.tsx` | ✅ Работает | Sources list, file upload, ingestion jobs, re-index |
| Conversations `/conversations` | `conversations/page.tsx` | ✅ Работает | List with filters |
| Test Console `/test-console` | `test-console/page.tsx` | ✅ Работает | Chat + voice preview, agent selector |
| Analytics `/analytics` | `analytics/page.tsx` | 🟡 Partial | Charts wrapper — needs real data |
| Billing `/billing` | `billing/page.tsx` | 🟡 Partial | Plan display, usage — needs ЮKassa |
| Billing Checkout `/billing/checkout` | `billing/checkout/page.tsx` | 🟡 Partial | Checkout flow — needs payment integration |
| Operator Console `/operator` | `operator/page.tsx` | 🟡 Partial | Queue UI — needs WebSocket live handoff |
| Settings: Security | `settings/security/page.tsx` | ✅ Работает | MFA setup/disable, recovery codes |
| Settings: Team | `settings/team/page.tsx` | ✅ Работает | Invite, role update, remove members |
| Settings: API Keys | `settings/api-keys/page.tsx` | ✅ Работает | Create, copy, revoke |
| Settings: Channels | `settings/channels/page.tsx` | ✅ Работает | Telegram, Twilio, WhatsApp, VK, SIP, iiko config |
| Settings: Audit | `settings/audit/page.tsx` | ✅ Работает | Audit logs list |
| Super Admin `/super-admin` | `super-admin/page.tsx` | 🟡 Partial | Tenants management — needs full CRUD |
| Widget `/widget/[agentId]` | `widget/[agentId]/page.tsx` | ✅ Работает | Embeddable chat widget |
| ROI Calculator `/roi-calculator` | `roi-calculator/page.tsx` | ✅ Работает | Interactive savings calculator |
| Status `/status` | `status/page.tsx` | ✅ Работает | Service health page |
| Docs `/docs` | `docs/page.tsx` | ✅ Работает | Documentation page |
| Privacy `/privacy` | `privacy/page.tsx` | ✅ Работает | Privacy policy |
| Terms `/terms` | `terms/page.tsx` | ✅ Работает | Terms of service |
| Onboarding `/onboarding` | `onboarding/page.tsx` | 🟡 Partial | Setup wizard — needs completion |

**Компоненты (16 штук):** ActionNotice, AuditLogsList, BrowserCallWidget, ChatWidget, ChatWidgetGate, ConversationsList, CopyButton, DashboardShell, EmptyState, KnowledgeSourceForm, MotionWrapper, OperatorConsole, ResultNotice, StatusPill, SubmitButton, VoiceRecorder.

**Server Actions (`actions.ts`, 713 LOC):** 25+ actions — agents CRUD, knowledge, chat, voice, auth (login/register/MFA/password), billing, team, API keys, pathways, outbound calls.

**Frontend API Client (`lib/core-api.ts`, 699 LOC):** Полный типизированный API client: fetch/mutate/patch/upload/delete + auth cookies. 25+ TypeScript типов.

**MVP Data Layer (`lib/mvp-data.ts`, 931 LOC):** Умный fallback — если backend недоступен, frontend показывает mock данные с маркировкой `state: "mock"`. Все data-fetching функции пробуют real API → fallback. Это умная деградация.

**Auth Layer (`lib/auth.ts`, 150 LOC):** HttpOnly cookie management для JWT access/refresh tokens, MFA setup/recovery. Secure, sameSite, production flag.

**Middleware (`middleware.ts`, 43 LOC):** Защита protected routes (dashboard, agents, knowledge, settings...) + redirect auth pages для залогиненных.

### 1.4 Инфраструктура

| Компонент | Файлы | Статус |
|-----------|-------|--------|
| Docker Compose (local) | `infra/docker-compose.local.yml` | ✅ PostgreSQL, Redis, Qdrant, MinIO |
| Docker Compose (prod) | `infra/docker-compose.yml` | ✅ Все сервисы + API + Web |
| Grafana | `infra/grafana/` | ✅ Dashboard configs |
| Prometheus | `infra/prometheus/` | ✅ Scrape configs |
| Alertmanager | `infra/alertmanager/` | ✅ Alert rules |
| GitHub Actions CI | `.github/workflows/ci.yml` | ✅ Backend lint/test + frontend lint/typecheck/build |
| GitHub Actions QA | `.github/workflows/qa.yml` | ✅ Quality gates |
| GitHub Actions Security | `.github/workflows/security.yml` | ✅ Dependency scan |
| Alembic migrations | `migrations/versions/` (7 files) | ✅ Initial + customers + agents + orders + testbed |
| Scripts | `scripts/` (4 files) | ✅ Seed, backup, migration, smoke |
| API Dockerfile | `apps/api/Dockerfile` | ✅ |
| Web Dockerfile | `apps/web/Dockerfile` | ✅ |

### 1.5 Тесты

| Файл | Тестов | Покрытие |
|------|--------|----------|
| `test_auth_security.py` | ~20 | JWT, MFA, refresh, recovery codes, tenant guard |
| `test_core_mvp_flow.py` | ~10 | Register → agent → knowledge → chat → dashboard |
| `test_channels.py` | ~8 | Telegram, VK, WhatsApp adapters |
| `test_iiko_integration.py` | ~6 | iiko auth, menu import, orders |
| `test_new_features.py` | ~12 | Mixed features |
| `test_production_api.py` | ~8 | Production API flows |
| `test_production_services.py` | ~6 | Production services |
| `test_sqlalchemy_store.py` | ~8 | DB persistence |
| `test_rag.py` + `test_rag_ingestion.py` | ~6 | RAG chunking, ingestion |
| `test_policy_validation.py` | ~4 | Agent policy checks |
| Остальные (12 файлов) | ~27 | Audit, DB, demo, encryption, handoff, health, LLM, memory, orders, parsers, threaded worker |
| **Итого** | **~105** | Backend unit/integration |

Playwright config есть (`playwright.config.ts`), но E2E тесты минимальны.

### 1.6 Документация (`docs/`)

- `INDEX.md` — общий индекс
- `architecture/overview.md` — архитектура
- `runbooks/` — local-development, production-services
- `api/` — API documentation
- `strategy/` — market benchmark, positioning, sales, pricing, master checklist и другие (18+ файлов)

---

## 2. ЧТО НУЖНО СДЕЛАТЬ (ПОЛНЫЙ СПИСОК)

### 🔴 P0 — КРИТИЧЕСКОЕ (без этого продукт не работает)

#### P0-1. Переключить default store на SQLAlchemy
**Что:** Сейчас `STORE_BACKEND=memory` (default). Перезапуск = потеря всех данных.
**Как:**
1. В `apps/api/app/settings.py` строка 39: изменить `default="memory"` → `default="sqlalchemy"`
2. В `.env.example` добавить `STORE_BACKEND=sqlalchemy`
3. В `apps/api/.env` добавить `STORE_BACKEND=sqlalchemy` и `DATABASE_URL=sqlite:///callforce.db` (для локальной разработки)
4. Прогнать все 105 тестов — убедиться что ничего не сломалось
5. Создать migration для fresh start: `cd apps/api && alembic upgrade head`
**Время:** 30 минут
**Тест:** `cd apps/api && python -m pytest tests/ -v` — все 105 должны пройти

#### P0-2. RAG: подключить Qdrant для реального поиска
**Что:** Сейчас RAG `retrieve_sources()` ходит в Qdrant, но если нет OpenAI API key — embeddings генерируются через SHA256 stub, что даёт случайные результаты.
**Как:**
1. Добавить локальный embedding model (sentence-transformers) как альтернативу OpenAI:
   - `pip install sentence-transformers` → в `pyproject.toml`
   - В `rag.py` → `generate_embeddings()`: если нет OpenAI key, использовать `SentenceTransformer("all-MiniLM-L6-v2")` (384 dims)
   - Обновить `QDRANT_VECTOR_SIZE` default → 384 для local mode
2. Убедиться что `upsert_chunks_to_qdrant()` вызывается при ingestion:
   - В `knowledge.py` endpoint `/upload` и `/ingest` уже вызывают `build_knowledge_chunks()` + `upsert_chunks_to_qdrant()` — проверить что это реально работает
3. Убедиться что `retrieve_sources()` возвращает реальные результаты при поиске
4. Добавить Qdrant в `.env`: `QDRANT_URL=http://localhost:6333` (вместо `:memory:`)
**Время:** 2-3 часа
**Тест:**
```bash
# Поднять Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Загрузить тестовый документ
curl -X POST http://localhost:8000/api/v1/knowledge/sources \
  -H "Authorization: Bearer <token>" \
  -d '{"title":"Меню","source_type":"manual","content":"Пепперони 599 руб. Маргарита 499 руб."}'

# Проверить поиск
curl http://localhost:8000/api/v1/chat/mock \
  -H "Authorization: Bearer <token>" \
  -d '{"agent_id":"<id>","message":"какие есть пиццы?","channel":"web_widget"}'
# Должен вернуть ответ с реальными данными из загруженного документа
```

#### P0-3. Telegram канал: production webhook
**Что:** Telegram adapter полностью реализован (`telegram_adapter.py`), но нужно:
1. Убедиться что webhook endpoint `/api/v1/telegram/webhook/{token}` правильно обрабатывает updates
2. Настроить `setWebhook` при подключении бота
3. Проверить что ответ реально отправляется через Bot API
**Как:**
1. Создать Telegram бота через @BotFather → получить token
2. В UI Settings → Channels → вставить token
3. В `apps/api/app/api/v1/telegram.py` убедиться что:
   - webhook регистрируется при connect: `POST /api/v1/agents/{id}/telegram/connect`
   - при получении update: parse → orchestrator → send response
4. Тестировать: написать боту в Telegram → получить ответ
**Время:** 1-2 часа (если код уже работает, нужна только проверка и debug)
**Тест:** Написать боту → получить осмысленный ответ

#### P0-4. Web Widget: persistent sessions
**Что:** Widget endpoint `/api/v1/widget/chat/{agent_id}` существует и работает.
**Как проверить:**
1. Открыть `http://localhost:3000/widget/<agent_id>`
2. Написать сообщение → получить ответ
3. Обновить страницу → история должна сохраняться (через session_id)
4. Embed script `public/widget.js` должен создавать iframe
**Время:** 1 час (проверка + fix если что-то сломано)
**Тест:** Открыть widget → написать 3 сообщения → обновить → история на месте

---

### 🟡 P1 — ВАЖНОЕ (нужно для первых клиентов)

#### P1-1. Scenario Builder — визуальный конструктор
**Что:** `scenario_engine.py` умеет интерпретировать pathway (nodes/edges), но нет UI.
**Как:**
1. `@xyflow/react` **уже установлен** (`package.json: "@xyflow/react": "^12.11.0"`) — ничего ставить не надо!
2. Создать страницу `/agents/[id]/pathway/page.tsx`:
   - Canvas с React Flow
   - Palette: Start, Say, Ask, Condition, Knowledge, Tool, Transfer, End
   - Properties panel для редактирования node.data.label
   - Save/Load через `saveAgentPathwayAction` / `getAgentPathwayAction` (уже есть в `actions.ts`!)
   - Validation: Start node exists, no dangling edges
3. Backend endpoint `POST /api/v1/agents/{id}/pathway` — уже должен быть (проверить)
4. Добавить кнопку "Конструктор" на странице агента
**Время:** 6-10 часов
**Тест:** Создать pathway из 5 узлов → save → reload → все на месте → publish agent → test chat follows pathway

#### P1-2. ЮKassa биллинг
**Что:** `billing_service.py` имеет ledger с idempotency, `billing.py` API — checkout/plans/invoices, но нет реальной ЮKassa.
**Как:**
1. `yookassa` **уже установлена** (`pyproject.toml: "yookassa>=3.0.0"`) — ничего ставить не надо!
2. В `apps/api/app/api/v1/billing.py`:
   - `POST /billing/checkout` → создать Payment через ЮKassa API
   - `POST /webhooks/yookassa` → обработать payment.succeeded/cancelled webhook
   - Проверка HMAC подписи webhook
3. В Settings добавить `YOOKASSA_SHOP_ID` + `YOOKASSA_SECRET_KEY`
4. Frontend `/billing/checkout` → редирект на ЮKassa payment page
**Время:** 4-6 часов
**Тест:** Создать тестовый платёж (ЮKassa sandbox) → webhook → статус обновлён

#### P1-3. Operator Console — live handoff
**Что:** `OperatorConsole.tsx` (15K LOC) + `OperatorConsoleContainer.tsx` существуют, API `POST /conversations/{id}/handoff` есть.
**Как:**
1. Добавить WebSocket endpoint для real-time уведомлений оператору
2. При вызове `escalate_to_human` tool → создать запись в operator_queue
3. Frontend: отображать очередь, позволять принять/отклонить
4. При принятии: блокировать AI ответы, показать transcript + summary
**Время:** 4-6 часов
**Тест:** В chat попросить "позовите менеджера" → оператор видит уведомление → принимает → AI молчит

#### P1-4. Analytics — реальные данные
**Что:** `analytics/page.tsx` + `AnalyticsCharts.tsx` + `ChartsWrapper.tsx` есть, backend `analytics.py` есть.
**Как:**
1. Backend: считать реальные метрики из conversations/messages/billing
   - Automation rate = resolved_by_ai / total_conversations
   - Response time = avg message latency
   - Topics = group by intent/unresolved
2. Frontend: привязать charts к real API data вместо mock
**Время:** 3-4 часа
**Тест:** Создать 10 conversations → analytics показывает реальные графики

#### P1-5. Deploy pipeline
**Что:** CI (lint/test/build) работает, но нет deploy.
**Как:**
1. Добавить `.github/workflows/deploy.yml`:
   - Build Docker images → push to registry
   - SSH deploy или docker-compose pull + restart на сервере
2. Staging environment: `docker-compose -f infra/docker-compose.yml up -d`
3. Production: добавить SSL (Let's Encrypt), nginx reverse proxy
**Время:** 4-6 часов
**Тест:** Push to main → auto-deploy to staging → smoke test → manual approve → production

---

### 🟢 P2 — УЛУЧШЕНИЯ (после запуска)

#### P2-1. Voice Pipeline — realtime SIP
**Что:** Гораздо более готово, чем казалось! `voice.py` (701 LOC) уже имеет:
- ✅ REST: STT→LLM→TTS (audio upload endpoint)
- ✅ WebSocket: `/voice/stream/{agent_id}` — full browser→STT→LLM→TTS→browser pipeline
- ✅ Twilio Media Stream: `/webhooks/twilio/stream/{agent_id}` с barge-in!
- ✅ Twilio TwiML: `<Gather>` speech recognition
- ✅ Outbound calls + SMS
- 🟡 `asterisk_ari_service.py` — skeleton для прямого SIP

**Осталось:**
1. **Twilio account** — ввести credentials, протестировать реальные звонки (~1-2 ч)
2. **Browser client** — `BrowserCallWidget` уже существует, но нужно тестировать WebSocket audio streaming (~2-3 ч)
3. **SIP direct (Asterisk/FreeSWITCH)** — это единственная реально большая задача (~1-2 недели)
**Время:** 1-2 дня для Twilio, 1-2 недели для native SIP
**Тест:** Позвонить на SIP номер → агент отвечает → conversation сохраняется

#### P2-2. Дополнительные интеграции
- **r_keeper:** Адаптер по образцу iiko (~1-2 дня)
- **AmoCRM:** OAuth + contacts/deals API (~2-3 дня)
- **Bitrix24:** OAuth/webhook + leads/contacts (~2-3 дня)
- **1C:** HTTP-сервис обмен (~3-5 дней)
**Тест для каждого:** Connect → sync data → verify in UI

#### P2-3. Load testing
**Как:**
```bash
# Установить k6
# Создать load test script
k6 run --vus 50 --duration 5m apps/api/load_tests/chat_flow.js
```
**Целевые метрики:** p95 < 2s for chat, p95 < 1.5s for voice

#### P2-4. Security hardening
- SAST: `semgrep --config auto apps/`
- Secret scan: `trufflehog git .`
- DAST: `zap-cli quick-scan http://localhost:8000`
- Pentest перед production

---

## 3. КАК ЗАПУСТИТЬ ЛОКАЛЬНО

### 3.1 Backend
```bash
cd apps/api

# Создать venv
uv venv
source .venv/bin/activate  # или .venv\Scripts\activate на Windows

# Установить зависимости
uv pip install -e ".[dev]"

# Настроить .env
cp ../../.env.example .env
# Отредактировать: STORE_BACKEND=sqlalchemy, DATABASE_URL=sqlite:///callforce.db

# Применить миграции
alembic upgrade head

# Запустить
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3.2 Frontend
```bash
cd apps/web

# Установить зависимости
npm install

# Настроить .env.local
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000" > .env.local
echo "NEXT_PUBLIC_TENANT_ID=00000000-0000-0000-0000-000000000001" >> .env.local

# Запустить
npm run dev
```

### 3.3 Инфраструктура (PostgreSQL, Redis, Qdrant, MinIO)
```bash
cd infra
docker compose -f docker-compose.local.yml up -d
```

### 3.4 Demo seed
```bash
cd apps/api
python -m scripts.seed_demo_data
# Или: make seed-demo
```

**Demo credentials:** `owner@demo.local` / `demo-password-123` (tenant `00000000-0000-0000-0000-000000000001`)

---

## 4. КАК ТЕСТИРОВАТЬ

### 4.1 Backend тесты
```bash
cd apps/api
python -m pytest tests/ -v
# Ожидаемый результат: 105 passed
```

### 4.2 Frontend проверки
```bash
cd apps/web
npx eslint .           # Линтер
npx tsc --noEmit       # TypeScript проверка
npm run build          # Production build
```

### 4.3 E2E smoke (ручной)
1. Открыть `http://localhost:3000` → landing page
2. Register → `/dashboard`
3. Create Agent → `/agents/new`
4. Upload Knowledge → `/knowledge`
5. Test Chat → `/test-console`
6. View Conversation → `/conversations/{id}`
7. Settings → `/settings/security` → MFA setup
8. Settings → `/settings/channels` → Telegram token
9. Widget → `/widget/<agent_id>` → send message

### 4.4 API smoke
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"company_name":"Test","owner_email":"test@test.com","owner_name":"Test","password":"testtest123"}'

# Login (получить access_token)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"testtest123"}' | jq -r '.access_token')

# Create agent
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Agent","channel":"telegram","prompt":"Ты помощник пиццерии"}'

# Health check
curl http://localhost:8000/api/v1/readiness
```

---

## 5. СТРУКТУРА ФАЙЛОВ (ПОЛНАЯ КАРТА)

```
callforce/
├── apps/
│   ├── api/                          # FastAPI Backend
│   │   ├── app/
│   │   │   ├── api/v1/              # 21 endpoint-файл
│   │   │   ├── channels/            # telegram, vk, whatsapp adapters
│   │   │   ├── contracts/           # voice, billing, action_engine contracts
│   │   │   ├── integrations/        # integration helpers
│   │   │   ├── main.py             # FastAPI entry point
│   │   │   ├── settings.py         # Pydantic settings
│   │   │   ├── store.py            # InMemory store (40K LOC)
│   │   │   ├── sqlalchemy_store.py # PostgreSQL store (74K LOC)
│   │   │   ├── orchestrator.py     # Dialog pipeline (391 LOC)
│   │   │   ├── llm_router.py       # LLM routing (252 LOC)
│   │   │   ├── rag.py             # RAG pipeline (247 LOC)
│   │   │   ├── security.py        # JWT, passwords, MFA
│   │   │   ├── db_models.py       # 20 SQLAlchemy models
│   │   │   └── ... (35 modules total)
│   │   ├── tests/                   # 26 test files, 105+ tests
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   └── web/                          # Next.js Frontend
│       ├── app/
│       │   ├── page.tsx             # Landing (666 LOC)
│       │   ├── actions.ts           # Server actions (713 LOC)
│       │   ├── components/          # 16 React components
│       │   ├── login/               # Auth pages
│       │   ├── register/
│       │   ├── dashboard/
│       │   ├── agents/              # Agent CRUD
│       │   ├── knowledge/           # Knowledge base
│       │   ├── conversations/       # Chat history
│       │   ├── test-console/        # Chat/voice testing
│       │   ├── analytics/           # Charts/reports
│       │   ├── billing/             # Plans/checkout
│       │   ├── operator/            # Operator console
│       │   ├── settings/            # Security, team, API keys, channels, audit
│       │   ├── super-admin/         # Platform admin
│       │   ├── widget/              # Embeddable widget
│       │   ├── roi-calculator/      # ROI calculator
│       │   └── ... (24 route dirs total)
│       ├── lib/                      # Auth, core-api client
│       ├── middleware.ts             # Auth + tenant routing
│       ├── Dockerfile
│       └── package.json
│
├── packages/
│   ├── shared-types/                 # TypeScript shared types
│   └── ui/                           # UI component library
│
├── infra/
│   ├── docker-compose.local.yml      # Local dev: PG, Redis, Qdrant, MinIO
│   ├── docker-compose.yml            # Production: all services
│   ├── grafana/                      # Dashboards
│   ├── prometheus/                   # Scrape configs
│   └── alertmanager/                 # Alert rules
│
├── migrations/
│   └── versions/                     # 7 Alembic migrations
│
├── scripts/                          # Seed, backup, migration, smoke
├── tests/integration/                # Integration test placeholder
├── docs/                             # Architecture, runbooks, strategy
├── .github/workflows/                # CI, QA, Security
├── .env.example                      # Environment template
├── Makefile                          # Dev commands
├── README.md                         # Project overview
├── PROJECT_COMPLETION_PLAN.md        # Original completion plan (925 lines)
└── MASTER_PLAN.md                    # ← ВЫ ЗДЕСЬ
```

---

## 6. ENV-ПЕРЕМЕННЫЕ (ПОЛНЫЙ СПРАВОЧНИК)

| Переменная | Default | Описание | Обязательно для prod |
|-----------|---------|----------|---------------------|
| `APP_ENV` | `local` | Окружение: local/test/staging/production | ✅ |
| `STORE_BACKEND` | `memory` | Store: `memory` или `sqlalchemy` | ✅ Сменить на `sqlalchemy` |
| `DATABASE_URL` | `postgresql://...localhost` | PostgreSQL connection string | ✅ |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL | ✅ |
| `QDRANT_URL` | `:memory:` | Qdrant URL | ✅ Сменить на `http://qdrant:6333` |
| `ACCESS_TOKEN_SECRET` | `local-development-token-secret` | JWT signing secret | ✅ Сменить! |
| `ACCESS_TOKEN_TTL_MINUTES` | `15` | JWT token lifetime | |
| `REFRESH_TOKEN_TTL_DAYS` | `30` | Refresh token lifetime | |
| `OPENAI_API_KEY` | `` | OpenAI API key for LLM/STT/TTS/embeddings | Рекомендуется |
| `VLLM_BASE_URL` | `` | Local vLLM endpoint | Альтернатива OpenAI |
| `VLLM_MODEL` | `Qwen/Qwen2.5-7B-Instruct` | vLLM model name | |
| `LLM_PROVIDER` | `auto` | LLM: auto/openai/local_vllm/mock | |
| `TELEGRAM_BOT_TOKEN` | `` | Telegram Bot API token | Для Telegram канала |
| `TWILIO_ACCOUNT_SID` | `` | Twilio SID | Для голосовых звонков |
| `TWILIO_AUTH_TOKEN` | `` | Twilio auth token | |
| `TWILIO_PHONE_NUMBER` | `` | Twilio phone number | |
| `YOOKASSA_SHOP_ID` | `` | ЮKassa shop ID | Для биллинга |
| `YOOKASSA_SECRET_KEY` | `` | ЮKassa secret | |
| `IIKO_API_LOGIN` | `` | iiko API login | Для iiko интеграции |
| `SENTRY_DSN` | `` | Sentry DSN | Для мониторинга |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Разрешённые origins | ✅ |
| `SMTP_HOST` | `` | SMTP server | Для email |
| `API_PUBLIC_URL` | `http://localhost:8000` | Public API URL | ✅ |
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | Frontend → Backend URL | ✅ |
| `NEXT_PUBLIC_TENANT_ID` | `` | Demo tenant ID | Для dev |

---

## 7. ПОРЯДОК РАБОТ (РЕКОМЕНДУЕМЫЙ)

```
Неделя 1: Фундамент
├── [30 мин] P0-1: STORE_BACKEND=sqlalchemy
├── [2-3 ч]  P0-2: Qdrant + sentence-transformers embeddings
├── [1-2 ч]  P0-3: Telegram production webhook test
└── [1 ч]    P0-4: Widget session persistence test

Неделя 2: Ключевые фичи
├── [6-10 ч] P1-1: Scenario Builder (React Flow)
├── [4-6 ч]  P1-2: ЮKassa billing
└── [3-4 ч]  P1-4: Analytics real data

Неделя 3: Operations
├── [4-6 ч]  P1-3: Operator Console live handoff
├── [4-6 ч]  P1-5: Deploy pipeline
└── [2-3 ч]  Onboarding wizard completion

Неделя 4+: Polish & Voice
├── P2-1: Voice pipeline (2-4 недели)
├── P2-2: Additional integrations
├── P2-3: Load testing
└── P2-4: Security hardening
```

---

## 8. ACCEPTANCE CHECKLIST

### Для MVP Launch ✅
- [ ] `STORE_BACKEND=sqlalchemy` — default, данные не теряются
- [ ] RAG возвращает реальные результаты из Qdrant
- [ ] Telegram бот отвечает на сообщения
- [ ] Web widget работает с persistent sessions
- [ ] Регистрация → агент → knowledge → chat → conversations — полный flow
- [ ] MFA, password reset, email verification — работают
- [ ] Landing page, pricing, legal pages — доступны
- [ ] Docker Compose поднимает всё одной командой
- [ ] CI pipeline проходит: lint + typecheck + tests + build
- [ ] 100+ backend тестов passing

### Для Production Release ✅
- [ ] ЮKassa биллинг работает (sandbox → production)
- [ ] Scenario Builder позволяет создавать сценарии
- [ ] Operator Console принимает эскалации
- [ ] Analytics показывает реальные метрики
- [ ] Deploy pipeline: push → staging → production
- [ ] SSL, nginx, домен настроены
- [ ] Backups настроены и проверены
- [ ] Monitoring alerts настроены
- [ ] Load test пройден (50+ concurrent users)
- [ ] Security scan пройден (no critical findings)
- [ ] Legal documents готовы (оферта, privacy, ПД)
- [ ] Voice pipeline работает E2E (хотя бы через WebSocket)
