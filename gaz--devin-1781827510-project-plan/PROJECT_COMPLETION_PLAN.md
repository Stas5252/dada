# План доведения AI-платформы поддержки клиентов до Production

Источник: `TZ_AI_Platform_4_0_final_full.docx`, версия 4.0 Final Full от 18.06.2026.

Дата первичного разбора: 2026-06-19.

Дополнительная стратегия “не просто MVP, а идеальная production-система”: [`docs/strategy/README.md`](docs/strategy/README.md).
Индекс markdown-документации: [`docs/INDEX.md`](docs/INDEX.md).

## 1. Текущее состояние проекта

### Что уже сделано в этой сессии

- Создан strategy pack в `docs/strategy`: market benchmark, positioning, sales funnel, production architecture, backend/frontend roadmap, QA/security/RF compliance, operations, master checklist.
- Создан общий индекс markdown-документации `docs/INDEX.md`.
- Добавлены presets/growth/pricing/pilot docs: industry presets, demo tenants, GTM playbook, product gap analysis, unit economics, pilot execution kit.
- Добавлены risk register и детальную экономику: pre-production checklists, P&L модель, breakeven, инвестиции по фазам.
- Добавлен реальный расчет при 0 ₽ вложений: API vs local GPU, себестоимость звонка/диалога, упаковка недорогих тарифов.
- Изучено ТЗ 4.0: продукт, архитектура, сайт, дашборд, БД, API, голос, чат, RAG, Action Engine, интеграции, безопасность, DevOps, биллинг, аналитика, тесты, приемка и запуск клиентов.
- Проверен репозиторий `StopIllusionist/gaz-`.
- Зафиксировано текущее состояние репозитория:
  - репозиторий пустой;
  - нет `README.md`;
  - нет `AGENTS.md`;
  - нет `CONTRIBUTING.md`;
  - нет `package.json`, `pyproject.toml`, `Makefile`;
  - нет `.pre-commit-config.yaml` и `.husky`;
  - кода, тестов, инфраструктуры и документации проекта пока нет.
- Создан этот markdown-документ как рабочая память проекта: что требуется, что не сделано, какой порядок разработки и какие критерии закрытия.
- Инициализирован стартовый skeleton монорепозитория:
  - `README.md`, `.env.example`, `Makefile`, `.gitignore`, `.pre-commit-config.yaml`;
  - `apps/api` FastAPI skeleton с `/api/v1/health`, tenant middleware и pytest-тестом;
  - `apps/web` Next.js skeleton с landing page и dashboard preview;
  - `packages/shared-types` и `packages/ui` с базовыми TypeScript exports;
  - `infra/docker-compose.local.yml` для PostgreSQL, Redis, Qdrant, MinIO, API и web;
  - `docs/architecture/overview.md` и `docs/runbooks/local-development.md`;
  - lockfiles для Python/Node зависимостей.
- Проверки skeleton пройдены: `make lint`, `make typecheck`, `make test`, `make build`, `npm audit --audit-level=moderate`, `pre-commit run --all-files`.
- Добавлен первый Core MVP vertical slice:
  - `POST /api/v1/auth/register`;
  - `GET /api/v1/tenants/{tenant_id}/dashboard`;
  - `GET/POST /api/v1/agents`, `POST /api/v1/agents/{agent_id}/publish`;
  - `GET/POST /api/v1/knowledge/sources`;
  - `GET /api/v1/conversations`, `GET /api/v1/conversations/{conversation_id}`;
  - `POST /api/v1/chat/mock`;
  - in-memory repository для локального MVP-сценария;
  - SQLAlchemy core DB models и SQL migration `migrations/versions/0001_core_mvp.sql`;
  - pytest-тесты happy path и tenant isolation;
  - frontend pages `/onboarding`, `/agents`, `/knowledge`, `/conversations`.
- Проверки после Core MVP slice пройдены: `make lint`, `make typecheck`, `make test`, `make build`.
- Интегрированы параллельные направления:
  - frontend MVP flows: reusable dashboard shell, onboarding, agents, knowledge, conversations, typed mock data client;
  - contract-first skeletons: Action Engine, voice state machine, iiko/webhook integrations, billing idempotency, masking, JSON Schemas;
  - DevOps/QA foundation: GitHub Actions QA workflow, audit/pre-commit targets, smoke/migration/backup runbooks and scripts.
- Усилен auth/RAG foundation:
  - PBKDF2 password hashing вместо хранения/игнорирования plain password;
  - HMAC-signed local access token с expiry payload и `ACCESS_TOKEN_SECRET`;
  - `POST /api/v1/auth/login` и negative login test;
  - RAG helper для chunking, source retrieval, grounded mock answer и no-answer policy;
  - SQLAlchemy database utilities, session scope, metadata create test and migration confidence type alignment;
  - тестовое покрытие выросло до 20 backend tests.
- Интегрирован второй batch production-readiness работ:
  - frontend real API wiring: typed server-side Core API client, `NEXT_PUBLIC_API_URL`, tenant demo handling, live/mock/error fallback;
  - RAG ingestion/Qdrant-ready pipeline: ingestion job/chunk schemas, deterministic local embedding, background job abstraction, `0002_rag_ingestion.sql`, runbook;
  - JWT/RBAC security hardening: token verification, bearer auth context, tenant mismatch rejection, role/permission helpers, audit event schemas;
  - SQLAlchemy-backed Core MVP repository: tenant/user/agent/knowledge/chat/dashboard persistence, password hash serialization, runtime switch via `STORE_BACKEND=sqlalchemy`, migration runner `make migrate`;
  - local production-service adapters: iiko menu/order idempotency, Telegram send idempotency, YooKassa payment idempotency, signed custom webhooks;
  - voice session service поверх voice state-machine contract;
  - billing usage charge service поверх idempotency ledger;
  - API endpoints для local iiko/Telegram/YooKassa/webhooks, voice sessions и billing usage charges;
  - readiness endpoint `/api/v1/readiness` и frontend dashboard секция Production readiness;
  - runbook `docs/runbooks/production-services.md`;
  - тестовое покрытие выросло до 44 backend tests.
- Runtime smoke test выполнен локально: UI dashboard/navigation прошли, API flow register/login → publish agent → knowledge source → mock RAG chat → dashboard counts прошел.
- Продолжение 2026-06-19:
  - установлен `uv` и через него поднят backend runtime на CPython 3.12.10;
  - добавлен детерминированный local demo tenant `00000000-0000-0000-0000-000000000001`;
  - demo seed содержит ресторан `Demo Pizza`, owner, 2 agents, 2 knowledge sources, 3 conversations;
  - demo seed подключен идемпотентно к `InMemoryStore` и `SqlAlchemyStore`;
  - добавлен `make seed-demo` и рабочий `scripts/seed_demo_data.py`;
  - исправлен local web live wiring: `NEXT_PUBLIC_API_URL` и `NEXT_PUBLIC_TENANT_ID` добавлены в `.env.example`, Docker Compose теперь указывает web на `http://api:8000`;
  - добавлены backend tests для demo seed и default demo dashboard;
  - business endpoints переведены на auth-bound tenant dependency: bearer token определяет tenant, `x-tenant-id` сверяется при наличии, legacy header fallback управляется `ALLOW_LEGACY_TENANT_HEADER`;
  - permissions подключены к agents/knowledge/conversations/dashboard/billing/integrations/voice routes;
  - добавлены tests для bearer-only business request, tenant mismatch, disabled legacy fallback и viewer denial;
  - добавлен typed mutation client для Core API и frontend server actions для create agent, create knowledge source и mock chat;
  - страницы `/agents/new`, `/knowledge` и `/test-console` теперь пишут в live Core API и показывают success/error notice;
  - `/test-console` добавлен в dashboard navigation и связывает созданный mock chat с `/conversations/{conversationId}`;
  - access token переведен с кастомного `devin-local` HMAC формата на JWT HS256 с `iss`, `sub`, `tenant_id`, `iat`, `exp`, `jti`;
  - добавлены opaque refresh tokens, `auth_sessions` storage, refresh rotation и logout revocation для `InMemoryStore` и `SqlAlchemyStore`;
  - добавлены endpoints `POST /api/v1/auth/refresh` и `POST /api/v1/auth/logout`;
  - добавлена migration `0004_auth_sessions.sql` и env-настройки `ACCESS_TOKEN_TTL_MINUTES`, `REFRESH_TOKEN_TTL_DAYS`;
  - добавлены tests для JWT token pair, refresh rotation/reuse rejection, logout revocation, tampered refresh token и SQLAlchemy auth sessions;
  - проверки прошли: backend `pytest` 56/56, `ruff`, `mypy`; frontend `lint`, `typecheck`, `build`, `npm audit`; runtime smoke health + auth login/refresh/logout + `/test-console`.
- Продолжение hardening-pass 2026-06-19:
  - проведен browser smoke через встроенный браузер по `/`, `/login`, `/register`, `/dashboard`, `/agents/new`, `/knowledge`, `/conversations`, `/test-console`, `/onboarding`, `/docs`, `/privacy`, `/terms`;
  - подтверждено, что русские строки в browser render корректные, а mojibake наблюдался только в PowerShell output;
  - убраны `href="#"` в footer, добавлены реальные страницы `/docs`, `/privacy`, `/terms`;
  - добавлен `ChatWidgetGate`: demo chat больше не мешает auth/workspace маршрутам и не создает лишний submit-button на login/register;
  - добавлена мобильная навигация `DashboardShell` через нативное `details` меню, desktop sidebar сохранен;
  - в Agent Builder и Knowledge Source Form prefilled demo text заменен на placeholders, чтобы пользователь не отправлял случайный demo-контент;
  - frontend logout теперь отзывает refresh token через `POST /api/v1/auth/logout`, а не только чистит cookies;
  - убран build-time dependency на Google Fonts: `next/font/google` заменен системным font stack, production build теперь проходит без сетевого fetch;
  - исправлен transcript detail role mapping: UI сравнивает сообщения с API role `customer`, а не устаревшим `user`;
  - backend rate limiter отключается под pytest, чтобы независимые TestClient flows не ловили общий 429 после нескольких регистраций;
  - backend Telegram/RAG/MFA/SQLAlchemy lint/type issues приведены к strict gates: добавлены missing imports, `raise ... from`, idempotency key, return annotations и bool assignment;
  - проверки прошли: frontend `eslint`, `tsc --noEmit`, `next build`; backend `ruff`, `mypy`, `pytest` 55/55.
- Продолжение auth/user-flow hardening 2026-06-19:
  - добавлены frontend routes `/forgot-password`, `/reset-password`, `/verify-email`;
  - добавлены server actions `requestPasswordResetAction` и `resetPasswordAction`;
  - добавлен `mutateCoreApiNoContent` для backend endpoints, которые корректно возвращают `204 No Content`;
  - login page теперь показывает success notice после смены пароля;
  - middleware больше не редиректит token-based страницы `/reset-password` и `/verify-email` из-за наличия auth cookie;
  - `ChatWidgetGate` дополнен `/verify-email`, чтобы чат не перекрывал auth/security states;
  - `ActionNotice` и `ResultNotice` переведены с несуществующих CSS-классов `notice*` на Tailwind styling;
  - browser smoke выполнен на свежем production build через `next start` на `http://127.0.0.1:3002`: desktop и mobile `/login`, `/forgot-password`, `/reset-password`, `/verify-email`, включая submit reset-request;
  - проверки прошли: frontend `eslint`, `tsc --noEmit`, `next build`; backend `ruff`, `mypy`, `pytest` 55/55; `npm audit --audit-level=moderate` вернул `0 vulnerabilities`.
- Продолжение security/account hardening 2026-06-19:
  - добавлена защищенная workspace-страница `/settings/security` в `DashboardShell` с текущим пользователем, статусом email, статусом MFA, запуском TOTP setup и формой подтверждения кода;
  - `DashboardShell` получил пункт `Security`, middleware защищает `/settings`, `ChatWidgetGate` скрывает demo chat на settings routes;
  - добавлены frontend server actions `startMfaSetupAction`, `verifyMfaSetupAction`, `cancelMfaSetupAction`;
  - временный TOTP setup secret хранится в короткоживущем httpOnly cookie `cf_mfa_setup`, а не в URL/query string и не в client state;
  - backend auth responses больше не отдают `totp_secret`: добавлена публичная модель `UserPublic` с `mfa_enabled`;
  - исправлен MFA login bug: при включенной MFA `POST /api/v1/auth/login` теперь выпускает непустой 5-минутный intermediate access token для `/auth/login/mfa`;
  - добавлен regression test `test_auth_user_responses_do_not_expose_totp_secret`, который включает MFA, проверяет `/auth/me`, MFA-login и отсутствие `totp_secret` в публичных ответах;
  - Playwright smoke на свежих runtime `http://127.0.0.1:8000` + `http://127.0.0.1:3002`: login demo owner -> `/settings/security` -> MFA setup -> mobile viewport; подтверждены отсутствие console errors, horizontal overflow, `href="#"` и chat widget на workspace security page;
  - проверки прошли: frontend `eslint`, `tsc --noEmit`, `next build`; backend `ruff`, `mypy`, `pytest` 56/56.
- Продолжение agent-flow hardening 2026-06-19:
  - backend agents API расширен: `GET /api/v1/agents/{agent_id}` и `PATCH /api/v1/agents/{agent_id}`;
  - `InMemoryStore` и `SqlAlchemyStore` получили `update_agent`; изменения prompt/channel инкрементируют version и возвращают агента в `draft`, чтобы published-конфигурация не менялась тихо;
  - frontend `/agents` больше не содержит декоративных кнопок: Edit ведет на `/agents/{agentId}`, Test открывает `/test-console?agentId=...`, Publish вызывает live server action;
  - добавлена страница `/agents/[agentId]` с редактированием name/channel/prompt, публикацией и переходом к тестированию;
  - `/test-console` принимает `agentId` query param и preselect выбранного агента;
  - create form больше не показывает устаревшее `Publish недоступен до API`;
  - добавлены backend tests для get/update/republish agent API и SQLAlchemy repository update flow;
  - Playwright smoke на свежем runtime: login demo owner -> create agent -> edit -> update prompt/channel -> publish -> test-console preselect -> mobile edit page; подтверждены отсутствие console errors, horizontal overflow, `href="#"`, а также рабочие edit/test/publish links;
  - проверки прошли: frontend `eslint`, `tsc --noEmit`, `next build`; backend `ruff`, `mypy`, `pytest` 56/56.
- Продолжение knowledge/RAG upload hardening 2026-06-19:
  - backend `/api/v1/knowledge/upload` теперь отклоняет пустые UTF-8 файлы и создает source + idempotent ingestion job для локального RAG pipeline;
  - добавлен regression test `test_knowledge_upload_and_ingestion_jobs_flow`: empty upload -> 400, file upload -> indexed source, ingestion job -> `completed`, повторный ingest возвращает тот же job id;
  - frontend `/knowledge` получил file upload state, живую ленту ingestion jobs, counters для processing/failed jobs и `Re-index` action через Core API;
  - `KnowledgeSourceForm` больше не мутирует DOM напрямую, показывает выбранное имя файла и не подставляет demo content в форму;
  - Playwright smoke на свежем runtime: login demo owner -> `/knowledge` -> upload `.md` -> ingestion jobs -> re-index -> mobile viewport; подтверждены absence of console errors, horizontal overflow и `href="#"`;
  - проверки прошли: backend `ruff`, `mypy`, `pytest` 57/57; frontend `eslint`, `tsc --noEmit`, `next build`.
- Продолжение MFA recovery/disable hardening 2026-06-19:
  - backend MFA расширен recovery codes: генерация человекочитаемых одноразовых кодов, хранение только SHA-256 hash с server secret, публичный счетчик `mfa_recovery_codes_remaining`;
  - `/api/v1/auth/login/mfa` принимает TOTP или single-use recovery code, использованный recovery code сразу списывается;
  - добавлены `POST /api/v1/auth/mfa/recovery-codes` для перевыпуска и `POST /api/v1/auth/mfa/disable` для выключения MFA после проверки TOTP/recovery code;
  - SQLAlchemy model и migration `0005_mfa_recovery_codes.sql` добавляют JSON-хранилище хэшей recovery codes;
  - frontend `/settings/security` показывает recovery codes после enable/regenerate, умеет перевыпускать codes и выключать MFA; `/login/mfa` принимает recovery code без mobile overflow;
  - regression tests покрывают redaction, счетчик codes, single-use recovery login, reuse rejection, regenerate и disable;
  - Playwright smoke: login demo owner -> MFA setup -> recovery codes -> regenerate через recovery code -> disable через новый recovery code -> mobile `/login/mfa`; подтверждены absence of console errors, horizontal overflow и `href="#"`;
  - проверки прошли: backend `ruff`, `mypy`, `pytest` 58/58; frontend `eslint`, `tsc --noEmit`, `next build`.
- Продолжение web-widget/runtime hardening 2026-06-20:
  - публичный `/api/v1/widget/chat/{agent_id}` больше не пишет turn в новый случайный conversation: widget session стабильно мапится в conversation UUID, история сообщений реально читается orchestrator-ом и сохраняется в store;
  - Telegram webhook переведен на тот же `record_chat_turn`, чтобы channel adapters не расходились по поведению conversation history;
  - widget endpoint получил validation `session_id`/`message`, response `conversation_id` и публичный rate limit `30/minute`;
  - `ChatWidget` и `/widget/[agentId]` перестали возвращать локальную demo-симуляцию: сообщения отправляются в backend через `NEXT_PUBLIC_API_URL`, а глобальный виджет использует `NEXT_PUBLIC_WIDGET_AGENT_ID`;
  - `apps/web/public/widget.js` исправлен: embed iframe теперь строит URL без синтаксической ошибки template literal;
  - CORS стал настраиваемым через `CORS_ORIGINS`, добавлен regression test на preflight для widget origin;
  - local rate limiter в `APP_ENV=local` использует `memory://`, чтобы публичные endpoints не падали 500 без локального Redis; staging/prod могут указать `RATE_LIMIT_STORAGE_URI`/`REDIS_URL`;
  - устранены реальные quality-gate долги в новых файлах: backend `ruff`/`mypy` снова зеленые, удалены unused imports, self-commentary comments и некорректные type ignores;
  - Playwright browser smoke на свежем runtime прошел: production web `/widget/389a4f13-05d3-5860-af9f-69bd9ce2493a` -> POST `/api/v1/widget/chat/...` -> UI показал ответ, backend вернул `200` и `conversation_id`;
  - проверки прошли: backend `ruff`, `mypy`, `pytest` 72/72; frontend `eslint`, `tsc --noEmit`, `next build`; root `npm run lint`, `npm run typecheck`, `npm run build`, `npm test`.
- Продолжение local-AI/LLM router hardening 2026-06-20:
  - исправлен критичный bug в `LLMRouter`: `VLLM_BASE_URL` теперь выбирает local OpenAI-compatible/vLLM provider даже без `OPENAI_API_KEY`; раньше router уходил в mock до проверки local endpoint;
  - добавлены настройки `LLM_PROVIDER`, `LLM_MAX_TOKENS`, `LLM_TEMPERATURE`, `LLM_TIMEOUT_SECONDS`, `OPENAI_FAST_MODEL`, `OPENAI_SMART_MODEL`, `VLLM_API_KEY`, `VLLM_MODEL`;
  - routing policy: `auto` использует local/vLLM для fast routes, OpenAI для smartest routes при наличии ключа, и deterministic mock только когда нет настроенного provider-а;
  - `/api/v1/readiness` теперь показывает provider `llm`: `configured` для `VLLM_BASE_URL`/`OPENAI_API_KEY`, `missing_secret` при явно выбранном provider-е без endpoint/secret, `local_stub` для local mock режима;
  - `.env.example`, local-development and production-services runbooks синхронизированы с реальными backend env-переменными;
  - regression tests добавлены для local vLLM routing без OpenAI key и readiness local LLM provider;
  - проверки прошли для целевого набора: backend `ruff`, `mypy`, `pytest tests/test_llm_router.py tests/test_health.py` 5/5.
- Продолжение voice preview / Twilio hardening 2026-06-20:
  - добавлен `POST /api/v1/voice/sessions/{session_id}/preview-turn`: текстовая реплика клиента проходит через voice-optimized orchestrator, обновляет `VoiceSession.transcript`, пишет conversation log и возвращает `conversation_id`;
  - `VoiceSessionService` получил `get_or_start_session` и `record_voice_turn`, чтобы customer/assistant turns не жили отдельно от state-machine;
  - `/voice/sessions/{session_id}/audio`, Twilio voice webhook и WebSocket voice stream теперь сохраняют voice transcript/session turn и conversation log;
  - исправлен outbound Twilio webhook URL: real/simulated calls теперь указывают на `/api/v1/voice/webhooks/twilio/voice/{agent_id}`, а не на несуществующий `/api/v1/webhooks/...`;
  - добавлены backend env-переменные `API_PUBLIC_URL`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`;
  - `/api/v1/readiness` теперь явно показывает `twilio_voice` и `speech_stt_tts`, чтобы real voice не считался готовым без Twilio и STT/TTS;
  - frontend `/test-console` получил text-based Voice preview form, которая после live API turn открывает сохраненный transcript;
  - создан competitor benchmark `docs/strategy/18-competitor-feature-benchmark-2026-06-20.md` по официальным источникам Intercom/Fin, Zendesk, Ada, PolyAI, Retell и Bland;
  - проверки прошли расширенным набором: backend `ruff`, `mypy`, full `pytest` 77/77; frontend/root `lint`, `typecheck`, `build`, `test`; runtime HTTP smoke подтвердил login -> agents -> voice preview -> saved conversation.
- GitHub handoff 2026-06-20:
  - локальный Git инициализирован прямо в рабочей папке проекта, потому что внешний `.git` в `C:\Users\пп\Desktop\проект` не распознавался Git как валидный репозиторий;
  - подключен `origin` к `https://github.com/Stas5252/dada.git`;
  - `.gitignore` расширен для локальных Playwright/test артефактов, чтобы в baseline commit не ушли runtime cache, логи, `.env`, `node_modules` и временные директории;
  - перед первым коммитом проверены GitHub refs, игнорируемые env-файлы, dry-run индекса, крупные неигнорируемые файлы и быстрый поиск секретов;
  - baseline прошел `pre-commit`, backend `ruff`/`mypy`/`pytest` 77/77 и root `lint`/`typecheck`/`build`/`test`.
- GitHub Actions hardening 2026-06-20:
  - после первого push исправлен backend CI setup: пакет устанавливается как editable `.[dev]`, поэтому `app` импортируется в GitHub runner так же, как в локальной среде;
  - frontend/security workflows переведены на корневой `package-lock.json`, `npm ci` и workspace-команды, чтобы cache/audit не искали несуществующий `apps/web/package-lock.json`;
  - backend dependency manifest и `uv.lock` синхронизированы с реально используемыми сервисными пакетами: `alembic`, `aiosmtplib`, Redis-ready `limits`, `twilio` и `sentry-sdk`;
  - test auth helper больше не зашивает local secret и выпускает JWT через текущий `ACCESS_TOKEN_SECRET`, поэтому feature-тесты проходят как в local, так и в GitHub CI;
  - перед повторным push локально пройдены `pre-commit`, backend `ruff`/`mypy`/`pytest` 77/77 и root `lint`/`typecheck`/`build`/`test`.
- Продолжение hardening-pass (Settings & Deployment) 2026-06-21:
  - Подключены frontend server actions в настройках API ключей (`settings/api-keys`): формы привязаны к `createApiKeyAction`, отзыв — к `revokeApiKeyAction`, добавлен вывод сгенерированного ключа при создании с CopyButton, demo fallback массивы полностью удалены.
  - Подключены frontend server actions в настройках команды (`settings/team`): привязка к `inviteTeamMemberAction`, `updateTeamMemberRoleAction` и `removeTeamMemberAction`, реализована возможность изменять роль и удалять участников из списка с динамическим подгружением текущего пользователя (чтобы защитить его от само-удаления), demo fallback списки удалены.
  - Заблокирован legacy tenant header fallback для staging/production путем принудительного задания `ALLOW_LEGACY_TENANT_HEADER: "false"` в `infra/docker-compose.yml`.
  - Все тесты и проверки пройдены со 100% успехом: backend `pytest` (96/96), frontend `lint`, `typecheck`, `build` и Playwright E2E smoke тесты (4/4).
- Интеграция и верификация каналов VK и WhatsApp (2026-06-21):
  - Добавлены интеграционные тесты для VK и WhatsApp в `apps/api/tests/test_channels.py` (число backend-тестов выросло до 102/102).
  - Реализованы кэшируемые фабрики `get_vk_adapter` и `get_whatsapp_adapter` с декоратором `@lru_cache` в `apps/api/app/service_factory.py`, предотвращающие пересоздание `DeduplicationStore` на каждый запрос.
  - Обновлены обработчики вебхуков в `vk.py` и `whatsapp.py` для использования кэшированных адаптеров из `service_factory`.
  - Исправлен NameError с `vk_token` в `vk.py` путем корректного извлечения `vk_group_token` из настроек тенанта.
  - Все 102 теста успешно проходят.
- Интеграция с iikoCloud (EPIC-INTEGRATIONS) 2026-06-21:
  - Добавлена новая секция настроек iikoCloud во фронтенд ЛК (`apps/web/app/settings/channels/page.tsx`) для ввода `iiko_api_login`, `iiko_organization_id` и `iiko_terminal_group_id`.
  - Обновлено действие `updateTenantSettingsAction` (`apps/web/app/actions.ts`) для валидации и сохранения учетных данных в настройки тенанта.
  - Реализован реальный клиент `IikoCloudClient` и его интеграция с `LocalIikoAdapter` (`apps/api/app/integration_services.py`) для автоматического импорта номенклатуры/меню, парсинга товаров, проверки на удаление и создания заказов доставки.
  - Написаны детальные тесты в `apps/api/tests/test_iiko_integration.py` с использованием моков HTTP-запросов и проверкой отказоустойчивости при сбоях сети.
  - Исправлены падения тестов из-за некорректной валидации UUID для строковых идентификаторов тенантов в `LocalIikoAdapter`.
  - Исправлен тест `test_threaded_backend_retries_and_fails` в `test_threaded_worker.py` с помощью изолированного мока `time` для предотвращения глобального изменения и гонок потоков.
  - Все 105 тестов успешно проходят.

### Вывод по статусу

Проект находится на стадии `1. Core MVP Chat` с расширенной production-readiness foundation. Базовая структура, quality gates, mock vertical slice, UI flows, contract skeletons, DevOps/QA foundation, API wiring, local demo tenant, live frontend mutations, RAG ingestion skeleton, JWT/refresh/session foundation, auth-bound business route tenant guard, SQLAlchemy/PostgreSQL repository runtime switch, local production-service adapters, их API endpoints, readiness dashboard, account security/MFA setup/recovery/disable flow, рабочий create/edit/test/publish agent flow, knowledge upload/re-index ingestion UX, реальный web widget chat path, local/OpenAI-compatible LLM routing и voice preview с transcript/conversation logging готовы. Следующий шаг - довести workspace до уровня top SaaS: production channel hardening для Telegram/widget, Qdrant-backed ingestion/retrieval, PDF/DOCX/URL ingestion, real integrations, настоящий SIP/STT/TTS realtime voice path и production observability/deploy.

## 2. Цель продукта

Создать российскую AI-платформу автоматизации поддержки клиентов, которая:

- принимает звонки и сообщения;
- отвечает по базе знаний;
- выполняет действия во внешних системах;
- передает сложные кейсы оператору;
- дает бизнесу аналитику, биллинг и прозрачный контроль качества;
- закрывает полный путь клиента: сайт -> регистрация -> онбординг -> подключение каналов -> настройка агента -> тестирование -> запуск -> аналитика -> биллинг -> поддержка.

Production-релиз должен включать:

- маркетинговый сайт;
- личный кабинет клиента;
- админ-панель платформы;
- операторскую консоль;
- конструктор сценариев;
- голосовой pipeline;
- чатовый pipeline;
- RAG и базу знаний;
- Action Engine;
- интеграции;
- PostgreSQL БД;
- биллинг;
- мониторинг;
- тесты;
- документацию;
- CI/CD;
- резервное копирование;
- контур 152-ФЗ.

Не входит в первый релиз:

- собственный дата-центр;
- собственная телефония уровня оператора связи;
- обучение LLM с нуля;
- полноценный marketplace приложений.

## 3. Объем MVP и Production

| Компонент | MVP | Production |
| --- | --- | --- |
| Сайт | Лендинг, тарифы, заявка | Кейсы, документация, блог, статус, legal-pages, demo request |
| Кабинет клиента | Загрузка знаний, Telegram, диалоги | Все каналы, сценарии, биллинг, аналитика, роли, настройки |
| Голос | 1 SIP-провайдер, входящие звонки | Несколько провайдеров, transfer, запись, barge-in, очереди, SLA |
| Чат | Telegram + web widget | Telegram, WhatsApp, VK, виджет, email позже |
| Интеграции | iiko меню/статус заказа | iiko, r_keeper, AmoCRM, Bitrix24, 1C, webhooks, custom tools |
| Тесты | Unit + минимальные integration | Unit, contract, e2e, load, latency, security, red-team, golden dialogs |

## 4. KPI, SLA и измеримые цели

| Метрика | MVP цель | Production цель |
| --- | --- | --- |
| Automation rate | >= 60% без оператора | >= 85% для типовых кейсов |
| Voice latency p50 | <= 1.2 сек | <= 800 мс после конца реплики |
| Voice latency p95 | <= 2.5 сек | <= 1.5 сек |
| Chat first response | <= 2 сек | <= 1 сек |
| STT WER RU | <= 18% на шумных звонках | <= 12-15% |
| RAG grounded accuracy | >= 80% | >= 92% |
| Tool success rate | >= 95% | >= 99% |
| Uptime app | 99.0% | 99.9% |
| Data loss | 0 критичных случаев | RPO <= 15 мин, RTO <= 2 часа |

## 5. Роли и основные пользовательские сценарии

### Роли

- `Owner клиента`: тариф, оплата, пользователи, каналы, интеграции, публикация агентов.
- `Admin клиента`: агенты, база знаний, сценарии, отчеты.
- `Оператор`: эскалации, ответы клиентам, закрытие диалогов.
- `Аналитик`: отчеты и выгрузки.
- `Super Admin платформы`: тенанты, биллинг, лимиты, health, поддержка, ручные правки.
- `Support платформы`: ограниченный доступ к логам без ПД, помощь с каналами и интеграциями.

### Use cases

- `UC-01 Онбординг ресторана`: регистрация -> тариф -> подключение канала -> загрузка меню/FAQ -> тест -> публикация.
- `UC-02 Входящий звонок`: SIP -> VAD/STT -> RAG/LLM -> action -> TTS -> лог.
- `UC-03 Заказ пиццы`: товары -> стоп-лист -> адрес -> оплата/подтверждение -> iiko order.
- `UC-04 Статус заказа`: идентификация -> API -> ответ.
- `UC-05 Эскалация`: триггер -> summary -> transfer/operator queue -> оператор видит контекст.

## 6. Целевая архитектура

Архитектура должна быть multi-tenant, модульной, с разделением realtime voice path и обычного backend path.

### Сервисы

| Сервис | Назначение | Технологии | Критичность |
| --- | --- | --- | --- |
| `api-gateway` | REST/WebSocket API, auth, tenant isolation | FastAPI, Pydantic, Uvicorn | P0 |
| `agent-orchestrator` | Диалог, память, RAG/tools | Python async, state machines | P0 |
| `voice-realtime` | SIP audio bridge, barge-in, streaming STT/TTS | Asterisk ARI, WebSocket, RTP | P0 |
| `rag-service` | Индексация, retrieval, citations, confidence | Qdrant, sentence-transformers | P0 |
| `action-engine` | Typed tool calls, retries, idempotency, audit | Python, JSON Schema | P0 |
| `scenario-engine` | Исполнение визуальных сценариев | DAG/state machine | P1 |
| `dashboard-web` | Кабинет, редактор, аналитика | Next.js, React Flow, Tailwind | P0 |
| `operator-console` | Очередь эскалаций и live handoff | Next.js, WebSocket | P1 |
| `billing-service` | Тарифы, лимиты, платежи | ЮKassa, Postgres | P1 |
| `analytics-service` | Метрики, отчеты, unresolved topics | Postgres MVP, ClickHouse optional | P1 |

### Данные и внешние компоненты

- PostgreSQL для основной БД.
- Redis для очередей/кэша.
- Qdrant для векторного поиска.
- S3-compatible object storage для файлов, аудио, документов, бэкапов.
- vLLM/OpenAI-compatible LLM endpoint.
- Faster-Whisper/STT.
- VAD.
- Streaming TTS: XTTS/Kokoro или выбранная модель.
- Asterisk/ARI для телефонии.
- Интеграции: iiko, r_keeper, AmoCRM, Bitrix24, 1C, webhooks, SIP providers, ЮKassa.

## 7. Целевая структура репозитория

```text
ai-support-platform/
  apps/
    api/
    web/
    operator-console/
    widget/
  services/
    agent-core/
    rag-service/
    action-engine/
    voice-realtime/
    billing-service/
    analytics-service/
  packages/
    shared-types/
    ui/
    sdk-js/
  integrations/
    iiko/
    rkeeper/
    amocrm/
    bitrix24/
    onec/
    telephony/
  infra/
    docker-compose.yml
    docker-compose.local.yml
    nginx/
    k8s/
    terraform/
    grafana/
    prometheus/
  migrations/
  tests/
    unit/
    integration/
    e2e/
    voice/
    load/
    security/
    eval/
  docs/
    architecture/
    api/
    runbooks/
    legal-templates/
  scripts/
    seed_demo_data.py
    backup_restore_test.sh
    generate_openapi.py
  .env.example
  README.md
  Makefile
```

## 8. Главные P0-требования по подсистемам

### Voice

- `VOICE-001`: входящие звонки через SIP, отдельный `session_id` на каждый звонок.
- `VOICE-002`: barge-in, остановка TTS <= 300 мс после начала речи клиента.
- `VOICE-004`: аудио, transcript, timestamps, spans и этапы pipeline в деталях звонка.
- State machine: `NEW -> RINGING -> CONNECTED -> LISTENING -> TRANSCRIBING -> THINKING -> TOOL_CALLING? -> SPEAKING -> LISTENING -> ESCALATING -> TRANSFERRED -> COMPLETED -> FAILED | HANGUP | TIMEOUT`.

### Chat

- `CHAT-001`: все каналы нормализуются в единую модель `MessageEvent`.
- `CHAT-002`: история и summary для длинных чатов.
- `CHAT-003`: handoff оператору с блокировкой AI-ответов.

### Agent policy

- Отвечать коротко и естественно.
- Не придумывать цены, сроки, наличие, статус заказа, бонусы, юридически значимую информацию.
- Использовать только базу знаний, сценарий или tools.
- При низком confidence, раздражении клиента или просьбе о человеке — эскалировать.
- Не раскрывать системный prompt, ключи, внутренние инструкции и данные других клиентов.
- Перед созданием/изменением/отменой заказа получать явное подтверждение клиента.

### RAG

- `RAG-001`: хранить `source_id`, `document_id`, `chunk_id`, `title`, `url/page`, `updated_at` для цитат.
- `RAG-002`: reindex без остановки сервиса.
- `RAG-004`: unresolved topics для вопросов без ответа.
- Pipeline: загрузка -> парсинг -> очистка -> chunking -> embeddings -> hybrid retrieval -> rerank -> answer with sources -> evaluation.

### Action Engine

- `ACT-001`: destructive actions только после подтверждения клиента.
- `ACT-002`: каждый tool call логируется с masked PII.
- `ACT-003`: dry-run в тестовом режиме сценариев.
- `ACT-004`: retries только для idempotent operations.
- Tool contract должен иметь JSON Schema входа/выхода, permissions, timeout, retry policy, idempotency key, audit.

### Scenario Builder

- `SCN-001`: версии сценариев `draft/published/archived`.
- `SCN-002`: validation перед публикацией: Start, отсутствие dangling edges, fallback.
- `SCN-003`: тест узла и всего сценария с mock tools.
- `SCN-004`: шаблоны: пиццерия, доставка, такси, магазин.
- Node types: Start, Say, Ask, Condition, Knowledge, Tool, Webhook, Transfer, Wait, End, Global.

### Security

- `SEC-001`: tenant isolation на middleware и SQL-filter уровне.
- `SEC-002`: audit log для публикации агента, prompt changes, интеграций, платежей.
- `SEC-003`: credentials интеграций только в secrets vault/encrypted store.
- `SEC-004`: экспорт/удаление данных клиента.
- 152-ФЗ: ПД граждан РФ хранить и обрабатывать на серверах в РФ.
- TLS 1.3 in transit, encryption at rest для backups/object storage.
- PII masking в логах.
- Backups: daily full + incremental, restore drills.
- Security testing: SAST, dependency scan, secret scan, DAST, pentest перед production.

## 9. Интеграции

| Интеграция | Функции | Приоритет | Особенности |
| --- | --- | --- | --- |
| iiko | Меню, стоп-лист, заказ, изменение/отмена, статус, клиенты/лояльность | MVP P0 | sync 5 мин, cache, idempotency, modifiers mapping |
| Webhook custom | POST event, ожидание ответа, подписи, retries | MVP P0 | HMAC signature, timeout, secret rotation |
| SIP providers | Zadarma/Mango/Novofon/Билайн | MVP P0 | abstraction, health checks |
| r_keeper | Меню, заказ, статус, лояльность | P1 | adapter interface как у iiko |
| AmoCRM | Контакты, сделки, заметки, задачи | P1 | OAuth, field mapping |
| Bitrix24 | Лиды, сделки, контакты, комментарии, задачи | P1 | OAuth/webhook, rate limits |
| ЮKassa | Подписки, платежи, чеки, webhooks | P1 | Idempotence-Key, reconciliation |
| 1C | Товары, остатки, заказы, контрагенты | P2 | HTTP-сервис/обмен, очереди |

## 10. PostgreSQL схема

БД multi-tenant. В каждой бизнес-таблице обязателен `tenant_id`. PII хранить минимально, в логах маскировать.

Ключевые таблицы:

- `tenants`, `users`, `memberships`;
- `agents`, `agent_versions`;
- `scenarios`, `scenario_versions`;
- `knowledge_sources`, `documents`, `chunks`;
- `conversations`, `messages`, `call_sessions`, `transcripts`;
- `tool_definitions`, `tool_calls`;
- `integrations`, `iiko_menus`;
- `customers`, `operator_queue`;
- `billing_accounts`, `subscriptions`, `usage_events`, `payments`;
- `audit_logs`, `latency_spans`;
- `eval_datasets`, `eval_cases`, `eval_runs`;
- `feature_flags`, `api_keys`.

Обязательные индексы и ограничения:

- `UNIQUE(tenant_id, name, version)` для versioned сущностей.
- `INDEX(tenant_id, created_at)` для аналитики.
- `INDEX(conversation_id, created_at)` для деталей диалога.
- `UNIQUE(idempotency_key)` для tool calls/payments.
- `GIN(metadata)` для RAG metadata filters.
- Partial indexes by status для очередей и открытых кейсов.

## 11. Backend API

Базовые правила API:

- `/api/v1`;
- JWT access 15 мин + refresh rotation;
- optional MFA;
- tenant_id берется из membership/context, не из client payload;
- Pydantic strict schemas;
- единый error format: `error_code`, `message`, `details`, `request_id`;
- rate limits per user/tenant/API key/channel webhook;
- Idempotency-Key для billing/tools/orders;
- cursor pagination, `limit <= 100`.

Ключевые endpoints:

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /me`
- `GET /tenants/{id}/dashboard`
- `POST /agents`
- `PATCH /agents/{id}`
- `POST /agents/{id}/publish`
- `POST /knowledge/sources`
- `POST /knowledge/reindex`
- `POST /chat/webhook/telegram/{token}`
- `POST /widget/events`
- `WS /voice/{session_id}`
- `POST /tools/execute`
- `GET /conversations`
- `GET /conversations/{id}`
- `POST /conversations/{id}/handoff`
- `POST /integrations/iiko/connect`
- `POST /billing/checkout`
- `POST /webhooks/yookassa`
- `GET /analytics/reports`

## 12. Frontend, сайт и UX

### Маркетинговый сайт

- Главная: hero, demo call, цифры, как работает, интеграции, кейсы.
- Продукт: голосовой агент, чат-агент, iiko/CRM actions, handoff, аналитика.
- Решения: пиццерии, доставка, такси, магазины, сервисные компании.
- Интеграции: iiko, r_keeper, AmoCRM, Bitrix24, 1C, Telegram, WhatsApp, SIP.
- Цены: тарифы, лимиты, перелимит, add-ons, FAQ.
- Документация: API, webhooks, JS widget, security, status.
- Legal: политика, оферта, согласие ПД, SLA, DPA.

### Кабинет

- Dashboard: KPIs, alerts, чеклист подключения.
- Agents: список, статусы, каналы, версия, test/edit/publish.
- Agent Builder: prompt, голос, модель, policy, сценарий, tools, knowledge.
- Pathway Editor: React Flow canvas, palette, properties panel, validation panel, test panel.
- Knowledge: sources, documents, sync status, unresolved questions, coverage score.
- Integrations: cards, status, connect wizard, logs, mapping.
- Conversations: filters, transcript, audio, tools, sources, summary.
- Operator Console: очередь, live chat/call, customer card, suggested reply, close reason.
- Analytics: automation, topics, failures, CSAT, latency, cost, export.
- Billing: plan, usage, invoices, payment method, limits.
- Settings: users, roles, brand, legal, retention, API keys.

### Design system

- Primary: `#2563EB`.
- Dark/navy: `#0F172A`.
- Success: `#16A34A`.
- Warning: `#F59E0B`.
- Danger: `#DC2626`.
- Dashboard background: `#F8FAFC`.
- Cards: `#FFFFFF`.
- Font: Inter или Manrope.
- Radius: `12px` cards, `8px` inputs/buttons.
- Accessibility: WCAG AA, keyboard navigation, visible focus, aria labels.

## 13. DevOps, инфраструктура и окружения

Окружения:

- `local`: Docker Compose, mock integrations, small models/fake providers.
- `dev`: автодеплой main/dev, тестовые БД, sandbox iiko/ЮKassa.
- `staging`: копия production без реальных ПД, load tests, release candidate.
- `production`: мониторинг, backups, alerts, WAF/reverse proxy, SLA.

CI/CD pipeline:

1. lint + typecheck + unit tests;
2. build docker images;
3. dependency/secret scans;
4. integration tests with docker-compose;
5. e2e tests on preview env;
6. migration dry-run;
7. deploy staging;
8. smoke tests;
9. manual approval for production;
10. deploy production + post-deploy smoke + rollback plan.

Production deployment targets:

- Backend: HA Compose/Kubernetes, rolling deploy.
- PostgreSQL: managed HA, PITR backups.
- Redis: persistence/sentinel.
- Qdrant: snapshots + replication.
- Object storage: versioning + lifecycle + encryption.
- Model server: GPU pool, autoscaling/queue, model registry.
- Telephony: active-passive Asterisk, provider failover.
- Frontend: CDN + blue/green.

## 14. Мониторинг и эксплуатация

Собирать:

- Metrics: HTTP latency, error rate, conversations, calls, STT/LLM/TTS latency, tool success, queue size, GPU utilization, cost.
- Logs: structured JSON logs with `request_id`, `tenant_id`, `conversation_id`, masked PII.
- Traces: OpenTelemetry spans `webhook -> agent -> RAG -> LLM -> tool -> response`.

P0 alerts:

- app down;
- DB down;
- payment webhook failing;
- SIP down;
- high 5xx;
- cross-tenant bug.

P1 alerts:

- p95 latency high;
- tool error spike;
- iiko sync fail;
- low disk;
- high GPU memory.

Runbooks нужны для:

- iiko API down;
- high LLM latency;
- SIP provider outage;
- DB slow;
- payment errors.

## 15. Биллинг и тарифы

| Тариф | Цена | Включено | Ограничения |
| --- | --- | --- | --- |
| Start | 2 990 руб/мес | 300 диалогов, чат, 1 агент, 1 канал, базовая аналитика | Без голоса и кастомных интеграций |
| Business | 7 990 руб/мес | 1000 диалогов, чат+голос, 3 канала, iiko, 3 пользователя | Перелимит 12 руб/диалог |
| Pro | 19 990 руб/мес | 4000 диалогов, 10 каналов, CRM, сценарии, аналитика, 10 пользователей | SLA best effort |
| Enterprise | от 49 990 руб/мес | Выделенный контур, SLA, custom integration, SSO optional | Индивидуальный договор |

Billing events:

- `dialog_completed`;
- `voice_minute`;
- `extra_number`;
- `voice_clone`;
- `onboarding`;
- `custom_integration`.

## 16. Аналитика

Отчеты:

- Executive summary: диалоги, automation rate, экономия операторов, cost, CSAT, SLA.
- Каналы: звонки/чаты по дням, источник, peak hours, missed calls.
- Качество агента: resolved, unresolved, hallucination flags, low confidence, failed intents.
- Эскалации: reasons, operator workload, time to accept, outcome.
- RAG coverage: uncovered questions, outdated docs, source quality.
- Интеграции: tool success/error, latency, API errors by provider.
- Финансы: usage by plan, overage, cost per channel, margin estimate.

## 17. Тестирование

Тесты являются обязательной частью релиза.

| Тип | Покрытие | Инструменты | Порог |
| --- | --- | --- | --- |
| Unit | validators, adapters, state machines | pytest, pytest-asyncio | >= 80% backend core |
| Contract | tools, webhooks, iiko/r_keeper/CRM schemas | pytest, schemathesis/jsonschema | 100% P0 contracts |
| Integration | Postgres/Redis/Qdrant/API/worker | docker-compose, pytest | P0 flows pass |
| E2E web | onboarding, knowledge upload, publish agent, dialog view | Playwright | critical journeys pass |
| E2E chat | Telegram/widget webhook -> answer -> log | pytest + mocked webhooks | p95 target |
| Voice latency | audio fixtures through VAD/STT/LLM/TTS | pytest, locust/k6, custom harness | p50/p95 within SLA |
| Load | chats/calls/tools/dashboard | k6, Locust | graceful degradation |
| Security | Auth, RBAC, tenant isolation, OWASP | semgrep, zap, custom tests | no critical/high |
| RAG eval | Golden Q/A, source grounding, no-answer | deepeval/custom | target accuracy |
| Red-team | prompt injection, jailbreak, data exfiltration | promptfoo/custom | no P0 leak |
| Billing | ЮKassa webhooks, idempotency, limits | pytest fixtures | no double charge |
| Backup restore | DB/object storage restore drill | scripts/runbooks | RPO/RTO met |

Critical test cases:

- `TC-VOICE-001`: barge-in stops playback <= 300 мс.
- `TC-VOICE-002`: 10 сек тишины -> reprompt -> close/escalate.
- `TC-ACT-001`: create order without confirmation -> tool not called.
- `TC-ACT-002`: duplicate ЮKassa webhook -> no double charge.
- `TC-RAG-001`: no knowledge answer -> no hallucination.
- `TC-SEC-001`: tenant A requests tenant B conversation -> 403/404 + audit.
- `TC-INT-001`: iiko timeout -> retry/fallback/alert.
- `TC-UI-001`: invalid Tool node -> publish disabled + validation error.
- `TC-BILL-001`: plan limit exceeded -> usage/overage/warning/blocking policy.
- `TC-OPS-001`: operator accepts escalation -> AI stops, summary/transcript visible.

## 18. Roadmap

| Этап | Срок | Что делаем | Exit criteria |
| --- | --- | --- | --- |
| 0. Discovery/Setup | 1 неделя | legal, providers, iiko доступы, дизайн, репозиторий, CI | decisions согласованы, backlog создан |
| 1. Core MVP Chat | 2-4 недели | auth, tenants, dashboard base, RAG, Telegram/widget, conversations | чат отвечает по KB и логирует диалоги |
| 2. Integrations MVP | 2-3 недели | iiko menu/status, Action Engine, tool logs, unresolved topics | агент получает статус заказа/меню через iiko |
| 3. Voice MVP | 3-5 недель | Asterisk/SIP, VAD/STT/TTS, voice session, audio logs, barge-in basic | 10 тестовых звонков E2E без P0 |
| 4. Builder + Handoff | 3-4 недели | Pathway editor, operator console, transfer, validation/testing | клиент сам создает и публикует сценарий |
| 5. Billing + Analytics | 2-3 недели | ЮKassa, plans, usage, invoices, dashboards | платный клиент оплачивает и видит usage |
| 6. Production Hardening | 3-4 недели | security, load tests, monitoring, backup, legal, docs, QA | release checklist закрыт |

## 19. Backlog

### EPIC-AUTH

- [x] Регистрация/логин: register/login, password hashing, JWT access, refresh rotation, logout revocation, password reset/email verification pages, rate limiting и базовый optional MFA есть.
- [x] RBAC/account management: role helpers и business route permission guard есть, team/user management, invite flow, role assignment UI подключены и функционируют.
- [x] Tenant middleware: auth-bound tenant context есть, legacy header fallback отключен в staging/prod via docker-compose.
- [x] API keys: подключено создание, отзыв и копирование API-ключей в UI настройках.
- [x] MFA optional: backend setup/verify/login, recovery codes, disable flow, публичные `mfa_enabled`/remaining codes, frontend `/settings/security` и browser smoke есть.

### EPIC-KB-RAG

- [x] Upload documents MVP: manual source endpoint, UTF-8 `.txt/.md/.csv` file upload, ingestion jobs, re-index API/UI и browser smoke есть.
- [x] Rich document ingestion: PDF/DOCX/URL crawler, real background queue workers и production retry policy.
- [x] URL crawler.
- [ ] iiko menu ingestion.
- [ ] Chunking/embedding: chunking helper есть, нужны embeddings + Qdrant write path.
- [ ] Qdrant retrieval.
- [x] Unresolved topics.

### EPIC-AGENT

- [ ] Agent config: create/list/publish skeleton есть, нужны версии и validation.
- [ ] Prompt policy.
- [ ] Memory summary.
- [ ] Scenario engine: voice state machine skeleton есть, нужен runtime сценариев.
- [ ] Tool calling: Action Engine contracts есть, нужен runtime registry/executor.
- [ ] Evaluation.

### EPIC-VOICE

- [ ] Asterisk setup.
- [ ] WebSocket bridge.
- [ ] VAD.
- [ ] STT.
- [ ] TTS.
- [ ] Barge-in: state machine contract есть, нужна realtime media implementation.
- [ ] Call recordings.

### EPIC-CHAT

- [ ] Telegram.
- [ ] Web widget.
- [x] WhatsApp: integration webhook, challenge/verification, and message adapter with stateful deduplication.
- [x] VK: community webhook confirmation and message adapter with stateful deduplication.
- [x] Message normalization: WhatsApp and VK channel adapters parse updates, normalize them to MessageEvent, check billing limit, resolve customer, run orchestrator, and record chat turns.

### EPIC-INTEGRATIONS

- [x] iiko: реальная интеграция с iikoCloud (авторизация, импорт номенклатуры/меню, создание заказов) реализована и протестирована.
- [ ] r_keeper adapter.
- [ ] AmoCRM.
- [ ] Bitrix24.
- [ ] 1C.
- [ ] Custom webhooks: signing contract есть, нужен runtime endpoint.

### EPIC-FRONTEND

- [ ] Marketing site: создан стартовый landing skeleton, требуется полный сайт.
- [/] Dashboard/settings: MVP UI flow, auth session cookies, security settings/MFA setup, live API wiring, team settings, API keys, analytics и mutation feedback есть; нужны billing settings и production tenant switch policy.
- [ ] Agent builder: create/edit/test/publish flow пишет в Core API; нужны full visual builder, advanced validation, policy/knowledge binding и publish gates.
- [ ] Pathway editor.
- [x] Knowledge UI: create-source form, file upload, ingestion jobs, re-index action и browser smoke пишут в Core API.
- [x] Test console: mock chat form пишет в Core API и открывает созданный conversation.
- [x] Analytics.
- [ ] Billing UI.

### EPIC-OPS

- [ ] Monitoring.
- [ ] Logs.
- [ ] Tracing.
- [ ] Backups: runbook + dry-run script есть, нужен real backup target.
- [ ] Runbooks: local/devops runbooks есть, нужны production incident runbooks.
- [ ] CI/CD: GitHub Actions QA workflow добавлен, нужны deploy/staging workflows после появления `main`.

### EPIC-QA

- [ ] Unit.
- [ ] Contract.
- [ ] E2E.
- [ ] Load.
- [ ] Security: auth/MFA recovery/disable regression tests есть; нужны SAST/secret scan/DAST, threat model, account recovery policy и pentest перед production.
- [ ] RAG eval.
- [ ] Voice latency.

## 20. Definition of Done для любой фичи

- [ ] Есть код, тесты, миграции, документация и OpenAPI schema.
- [ ] Feature работает локально и на staging.
- [ ] Пройдены unit/integration/e2e тесты для затронутого функционала.
- [ ] Добавлены метрики, structured logs и audit events, если есть бизнес-действия.
- [ ] Учтены tenant isolation, RBAC, PII masking и secrets handling.
- [ ] Для UI есть loading/empty/error/success states и адаптивность.
- [ ] Для интеграций есть contract tests и mock server.
- [ ] Для новых tools есть JSON Schema, policy, timeout, retries, idempotency.
- [ ] Обновлены docs/runbook, если изменилось поведение production.

## 21. Release acceptance checklist

- [ ] Маркетинговый сайт доступен, адаптивен, содержит тарифы, demo CTA, legal pages.
- [ ] Пользователь может зарегистрироваться, создать tenant, подключить тариф и войти в кабинет.
- [ ] Клиент может создать агента, загрузить базу знаний, подключить Telegram/web widget и протестировать ответ.
- [ ] Клиент может подключить iiko, синхронизировать меню/стоп-лист и получить статус заказа через агента.
- [ ] Голосовой звонок проходит end-to-end: SIP -> STT -> LLM/RAG/tool -> TTS -> запись лога.
- [ ] Barge-in, silence handling, hangup, transfer работают по state machine.
- [ ] Операторская консоль принимает эскалации и показывает summary, transcript, данные клиента, историю tools.
- [ ] Все P0 API имеют тесты, auth, tenant isolation, audit logs.
- [ ] Биллинг создает платеж, принимает webhook, учитывает usage и лимиты тарифа.
- [ ] Dashboard показывает аналитику, unresolved topics, latency, usage, стоимость.
- [ ] Мониторинг и алерты настроены; есть healthchecks и runbooks.
- [ ] Backups настроены и восстановление проверено.
- [ ] Документация запуска, `.env.example` и onboarding checklist есть в репозитории.

## 22. Чек-лист запуска нового клиента

- [ ] Создан tenant, owner подтвердил email и принял оферту/ПД документы.
- [ ] Выбран тариф, настроен способ оплаты, выставлены лимиты.
- [ ] Подключены каналы: Telegram/виджет/SIP/WhatsApp по необходимости.
- [ ] Подключена iiko/r_keeper/CRM или custom webhook; health check зеленый.
- [ ] Загружена база знаний: меню, FAQ, доставка, акции, политика возвратов, контакты.
- [ ] Прогнан coverage audit: нет критичных пробелов.
- [ ] Создан агент из шаблона, настроен голос, tone of voice, политика эскалации.
- [ ] Сценарий протестирован в chat preview, voice preview и 5 реальных тестовых звонках.
- [ ] Операторы добавлены, очередь настроена, рабочее время и fallback callback заданы.
- [ ] Согласован текст disclosure: клиент понимает, что общается с AI.
- [ ] Включен production mode, alerts, daily summary для owner.

## 23. Legal-документы, которые нужно подготовить

- [ ] Публичная оферта SaaS.
- [ ] Политика конфиденциальности.
- [ ] Согласие на обработку персональных данных.
- [ ] Согласие/правила для записи звонков и использования AI-оператора.
- [ ] DPA/поручение обработки ПД для B2B клиентов.
- [ ] SLA и регламент поддержки.
- [ ] Политика хранения и удаления данных.
- [ ] Согласие на клонирование голоса, если функция включается.

## 24. Риски и меры

| Риск | Вероятность | Влияние | Митигирование |
| --- | --- | --- | --- |
| Latency выше ожиданий | Средняя | Высокое | Streaming, smaller model fallback, caching, GPU scaling, latency budget |
| Галлюцинации агента | Средняя | Высокое | RAG citations, confidence thresholds, no-answer policy, eval tests |
| Ошибочный заказ/отмена | Низкая/средняя | Высокое | Explicit confirmation, idempotency, audit, rollback/compensation |
| Плохая база знаний клиента | Высокая | Среднее | Coverage score, onboarding checklist, unresolved topics, templates |
| Сбой iiko/API | Средняя | Высокое | Cache, retries, circuit breaker, operator fallback |
| 152-ФЗ/ПД нарушения | Низкая при контроле | Критичное | Data localization, legal docs, access control, audit, retention |
| GPU стоимость | Высокая на старте | Среднее | Rental, quantization, batching, tariffs, capacity planning |
| Клиент ожидает 100% замены операторов | Средняя | Среднее | Sales messaging: 85-90% типовых кейсов + handoff |

## 25. Нерешенные решения перед стартом разработки

Эти вопросы нужно закрыть до активной реализации:

- [ ] Подтвердить список каналов MVP: Telegram + web widget + один SIP provider.
- [ ] Выбрать SIP-провайдера для MVP: Zadarma, Mango, Novofon, Билайн или другой.
- [ ] Получить iiko sandbox/production доступы и примеры меню/заказов.
- [ ] Подтвердить ЮKassa аккаунт, webhook policy и требования к чекам.
- [ ] Утвердить legal-пакет: оферта, privacy, ПД, DPA, SLA.
- [ ] Подтвердить тарифы и ограничения.
- [ ] Выбрать модели STT/LLM/TTS для local/RF infrastructure.
- [ ] Выбрать российский hosting/object storage/GPU provider.
- [ ] Решить, нужен ли WhatsApp в MVP или после MVP.
- [ ] Подготовить Figma-дизайн минимального набора экранов.

## 26. Первый практический план работ для следующей сессии

1. Довести auth до уровня топовых SaaS после JWT/refresh/logout slice:
   - MFA admin enforcement, re-enroll policy и recovery-code rotation policy для owner/admin ролей;
   - team/user management, invite flow и role assignment UI;
   - API keys/service accounts;
   - frontend auth session и tenant switch policy вместо public demo assumptions;
   - отключить `ALLOW_LEGACY_TENANT_HEADER` для staging/prod;
   - persisted audit log UI/export для login/refresh/logout/reset/MFA.
2. Довести live MVP UI flows после базовых mutations:
   - привязать frontend к auth session вместо public demo tenant;
   - довести agent builder до advanced validation, policy/knowledge binding и publish readiness gates;
   - довести rich document ingestion для knowledge sources: PDF/DOCX/URL crawler, background queue workers, retries и source detail page;
   - покрыть оставшиеся create source/test chat сценарии постоянными Playwright e2e smoke-проверками в CI;
   - связать demo tenant с dashboard без mock fallback для staging/prod.
3. Реализовать channel layer MVP:
   - Telegram webhook endpoint с dedup/idempotency;
   - web widget session/message API;
   - conversation normalization;
   - operator handoff status.
4. Усилить RAG:
   - production document ingestion для PDF/DOCX/URL;
   - Qdrant upsert/search adapter behind local stub interface;
   - unresolved topics;
   - golden questions for `restaurant_delivery_ru_v1`.
5. Production readiness:
   - PostgreSQL as default for non-local;
   - Alembic or hardened migration runner;
   - structured logs/correlation id;
   - rate limiting and incident/security runbooks.
6. После каждого завершенного блока обновлять:
   - раздел 1: что сделано и проверки;
   - раздел 19: backlog status;
   - `docs/strategy/09-master-checklist.md`;
   - соответствующий runbook.

## 27. Правило ведения этого документа

После каждой значимой задачи обновлять:

- раздел 1: что сделано;
- раздел 19: чекбоксы backlog;
- раздел 20: DoD по реализованным фичам;
- раздел 21: release acceptance;
- раздел 25: закрытые/открытые решения;
- раздел 26: следующий практический план.

Если в проект добавляется код, рядом должны появляться тесты, документация, конфигурация запуска и проверки качества.
