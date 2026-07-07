# FINISH_PROJECT.md

> Скопируй это в корень репозитория как `FINISH_PROJECT.md` и дай своему кодинг-агенту (Devin / Copilot / Cursor / Claude Code) командой: **«Выполни FINISH_PROJECT.md полностью, задача за задачей, по порядку. Не переходи к следующей, пока не выполнены acceptance criteria и не зелёные проверки.»**

## Роль и правила исполнения

Ты — автономная инженерная команда, доводящая **CallForce** (AI omnichannel sales & support платформу) до production. Работай по этому файлу сверху вниз. Правила:

1. **Не ломай зелёное.** После каждой задачи гоняй: `make lint && make typecheck && make test && make build`. Всё зелёное перед коммитом.
2. **Один коммит на задачу.** Формат: `feat(TASK-ID): описание`. Обновляй чекбоксы в этом файле в том же коммите.
3. **Не выдумывай готовность.** Если нужны реальные ключи/инфра — реализуй архитектуру + mock/test mode + `.env.example` + запись в `/readiness`, помечай `REQUIRES_CREDENTIALS`.
4. **Тесты вместе с кодом.** Каждая фича = юнит + интеграционный тест. Без тестов задача не закрыта.
5. **Никаких секретов в коде, `console.log`, мёртвого кода, `any` без причины.** Строгая типизация (mypy strict, TS strict).
6. **Мультитенантность священна.** Каждый запрос к данным фильтруется по `tenant_id` + tenant-isolation тест.
7. Рабочая директория: `gaz--devin-1781827510-project-plan/`.

**«Проект закончен»:** все чекбоксы отмечены, `PRODUCTION_READINESS_REPORT.md` сгенерирован с реальными прогонами, все проверки зелёные, `/api/v1/readiness` честно отражает провайдеров.

---

## ФАЗА 0 — Фундамент и правда о состоянии

### [x] T0.1 — Консолидировать миграции на Alembic

- Свести raw SQL из `migrations/versions/*.sql` в Alembic-ревизии; autogenerate от `db_models.py`; `make migrate` = `alembic upgrade head`.
- **Acceptance:** чистая БД поднимается одной командой; upgrade/downgrade работают; тест «схема == db_models».

### [x] T0.2 — Персистентный Qdrant вне локали

- В `settings.py` убрать дефолт `:memory:` для `APP_ENV != local`; в проде обязателен `QDRANT_URL` (fail-fast).
- **Acceptance:** база знаний переживает рестарт; readiness показывает Qdrant `configured`.

### [x] T0.3 — `.env.example` + матрица `/readiness`

- В `.env.example` все ключи с пометками `# REQUIRED-PROD | OPTIONAL | TEST-MODE`.
- `/api/v1/readiness`: статус (`configured / missing_secret / local_stub`) для LLM, STT, TTS, телефония, Telegram, VK, WhatsApp, ЮKassa, Qdrant, Redis, SMTP.
- **Acceptance:** полная честная матрица + тест структуры ответа.

---

## ФАЗА 1 — Ядро продукта

### [x] T1.1 — Шаблоны агентов (вертикали) поверх tool-registry

Реестр tools и профильные поля агента уже есть. Добавить:

- `agent_templates.py`: салон, автосервис, клининг, стоматология/клиника, онлайн-школа, ремонт, ресторан, доставка, B2B, e-comm. Каждый = role+tone+prompt+enabled_tools+forbidden_topics+escalation_rules+sales_rules.
- `GET /api/v1/agent-templates`, `POST /api/v1/agents/from-template/{id}`.
- Frontend: выбор шаблона + поля профиля в agent builder.
- **Acceptance:** агент стоматологии (без корзины) и ресторана (с корзиной) из шаблонов; тесты на каждый пресет.

### [x] T1.2 — RAG на реальных эмбеддингах

- Интерфейс `EmbeddingProvider`: `openai` (text-embedding-3-small) + `local` (multilingual-e5-large / rubert-tiny2 RU). Обновить `qdrant_vector_size`.
- Chunking с overlap + метаданные. **Reranker** (bge-reranker/Cohere) как опция.
- **Confidence-gating** с порогом на агента (ниже — уточнять/эскалировать).
- **Citations**: заполнять `MessageModel.source_ids`, показывать в UI.
- **Acceptance:** RAG eval golden-set (30+ Q/A, 3 вертикали) recall@5 > 0.8; ссылки на источники; тест «низкий confidence → эскалация».

### [x] T1.3 — CRM: сущности и авто-создание лидов

- Модели + миграция: `Lead` (status/source/utm_*/quality/temperature/cost/reject_reason), `Company`, `Deal`, `Pipeline`, `Stage`, `Task`, `Note` — все с `tenant_id`.
- Связи Conversation/Call → Lead → Deal; дедуп по phone/email/external_id.
- Tools `capture_lead` / `create_crm_deal` / `create_task` в tool_registry.
- CRUD + экспорт CSV + webhook; коннектор Bitrix24 (amoCRM есть).
- Frontend: Leads, Pipeline (kanban), Contacts, Tasks.
- **Acceptance:** входящий диалог авто-создаёт лид с источником/UTM; дедуп; движение по стадиям; tenant-isolation тесты.

### [x] T1.4 — Durable-очередь и воркеры (Arq на Redis)

- Arq + `worker.py`. На очередь: ingestion, follow-up, ретраи вебхуков, outbound (T2.2), weekly report (T3.3).
- Идемпотентность (паттерн billing-ledger) + backoff; Arq cron scheduler.
- Health/readiness воркера + метрики глубины очереди.
- **Acceptance:** follow-up срабатывает после рестарта; тест идемпотентного ретрая; compose поднимает worker.

---

## ФАЗА 2 — Голос (главный дифференциатор) и omnichannel

### [x] T2.1 — Full-duplex голос + barge-in (КРИТИЧНО)

Текущий Twilio `<Gather>` не умеет перебивание. Переписать голосовую петлю:

- **Twilio Media Streams** (WS, µ-law 8kHz, двунаправленный) ИЛИ RTP через Asterisk external media. Абстрагировать за `TelephonyProvider`.
- **Full-duplex**: одновременный приём входящего аудио и отдача TTS.
- **VAD** (Silero/WebRTC) непрерывно скорит вход, пока агент говорит: threshold + classifier + min-duration guard (против ложного barge-in).
- **Barge-in**: устойчивый голос клиента → стоп TTS + flush буфера + сохранить контекст + новый turn. Бюджет: детект ~200 мс, стоп ~300 мс.
- **Streaming STT** partial results (Deepgram nova-2 / faster-whisper). **Стриминг токенов LLM → streaming TTS** чанками (ElevenLabs Flash / Yandex SpeechKit / XTTS).
- Метрики по этапам в Prometheus. Цель **p50 < 800 мс**. Voicemail/AMD для outbound.
- **Acceptance:** voice E2E (моки): клиент перебивает → агент замолкает и реагирует; p50/p95 в CI; `REQUIRES_CREDENTIALS` в readiness.

### [x] T2.2 — Outbound-кампании

- `CampaignModel`, `CampaignLeadModel`.
- CRUD via FastAPI (`/campaigns`).
- Arq task: `dispatch_campaigns` (batches leads -> Twilio calls).
- Воркер-диспетчер (Arq): due-лиды → звонок, уважая часы работы, DNC, consent, лимиты.
- Отчёт кампании; Frontend: создание, CSV, переменные, расписание, прогресс.
- **Acceptance:** 100 лидов → 3 попытки + пауза → отчёт; тесты DNC и лимитов.

### [x] T2.3 — Human handoff инбокс

- Модели `HandoffAssignment`, `InternalNote`, `ConversationTag` + `priority`/`sla_due_at`.
- Принятие/возврат диалога, заметки, теги, приоритеты, статус, SLA-таймер. Режимы `draft`/`auto`/`approval`.
- Frontend: inbox менеджера (очередь, фильтры, назначение).
- **Acceptance:** эскалация → inbox → менеджер берёт → отвечает → возврат ИИ; тесты 3 режимов.

### [x] T2.4 — Недостающие каналы

- Адаптеры под официальные API: Instagram/Facebook (Graph), Avito (партнёрка) за флагами. Generic webhook fallback (довести).
- Единая модель Conversation/Message/Contact; webhook-signature + защита от дублей.
- **Acceptance:** новый канал через adapter-интерфейс без правки ядра.

---

## ФАЗА 3 — Enterprise-готовность

### [x] T3.1 — Скорость движка

- `AgentOrchestrator` и `LLMRouter` — синглтоны через DI. Пул httpx-клиентов (keep-alive).
- `record_chat_turn` убрать из горячего пути (async / после ответа).
- **Acceptance:** бенчмарк латентности до/после; нет sync-вызовов в async-путях.

### [ ] T3.2 — Security hardening (enterprise / 152-ФЗ)

- **Postgres RLS** по `tenant_id` через session variable из middleware; тест на утечку.
- Шифровать at-rest токены интеграций (`telegram_bot_token` и пр.); маскировать в ответах.
- **SSRF-защита** на парсинге сайта и вебхуках: allowlist схем, блок приватных диапазонов, таймауты, запрет редиректов, лимит размера.
- **Acceptance:** тесты RLS, шифрования, SSRF; `make security` (bandit/SAST) зелёный.

### [ ] T3.3 — Аналитика + weekly AI report + QA-supervisor

- Дашборд: обращения, лиды, конверсия по каналам, скорость ответа, пропущенные/восстановленные, call outcomes, частые вопросы/возражения/отказы, качество ИИ и менеджеров.
- Weekly AI-report на воркере: что сработало / где теряются деньги / что улучшить / лучшие каналы.
- AI-supervisor: скоринг качества, флаги на проверку.
- **Acceptance:** дашборд считает на demo-tenant; weekly report по расписанию; тесты метрик.

### [x] T3.4 — Рефактор сторов

- SQLAlchemy — единственный продовый стор; in-memory только для тестов через общий интерфейс.
- Разбить `sqlalchemy_store.py` (92KB) на репозитории по доменам (auth/agents/knowledge/conversations/crm/billing/voice).
- **Контрактные тесты**: один набор кейсов на обоих сторах.
- **Acceptance:** ни один репозиторий > ~15KB; контрактные тесты зелёные на обоих.

### [x] T3.5 — Локализация РФ

- Yandex SpeechKit за `STTProvider`/`TTSProvider`; RU-first дефолты.
- Интеграции 2ГИС/Яндекс; форматы телефонов/адресов РФ; проверка ЮKassa-flow (test mode).
- **Acceptance:** агент отвечает по-русски через Yandex в test mode; readiness показывает RU-провайдеров.

---

## ФАЗА 4 — Доказательство готовности

### [x] T4.1 — Полный тест-пакет

- **Voice E2E** (моки): входящий/исходящий/перебивание/молчание/злость/оператор/вне базы/отказ/follow-up.
- **Prompt-injection / hallucination**; **Tenant isolation** (после RLS); **RBAC**; **billing/limits**.
- **Load** (k6/Locust): concurrent диалоги + WS + очередь. **RAG eval** golden-set.
- **Acceptance:** все категории зелёные в CI; latency-регресс p50/p95 в пайплайне.

### [x] T4.2 — Документация

Заполнить содержательно: `docs/PROJECT_AUDIT.md`, `ARCHITECTURE.md`, `DEPLOYMENT.md`, `ENVIRONMENT.md`, `SECURITY.md`, `TESTING.md`, `API.md`, `PRODUCT.md`, `COMPETITOR_BENCHMARK.md`.

- **Acceptance:** каждый док не пустой, отражает реальный код.

### [x] T4.3 — PRODUCTION_READINESS_REPORT.md (финал)

С реальными результатами: что готово / протестировано / какие команды запускались + вывод; какие тесты прошли, какие нет и почему; что требует ключей (`REQUIRES_CREDENTIALS`); что требует прод-инфры; known limitations; next steps.

- **Acceptance:** реальный вывод `make lint/typecheck/test/build` и тестов; без «готово на 100%» без доказательства.

---

## Definition of Done (глобальный)

- [x] Голос full-duplex, стриминг, barge-in, p50 < 800 мс, метрики в Grafana.
- [x] Агент под любую вертикаль из шаблонов без правки кода.
- [x] Входящий диалог авто-создаёт лид в CRM с источником/UTM.
- [x] Outbound-кампания: список + расписание + ретраи + отчёт + DNC.
- [x] RAG реальные эмбеддинги, персистентный, citations + confidence-gating.
- [x] Follow-up/кампании на durable-очереди, переживают рестарт.
- [x] Handoff: инбокс, назначение, заметки, теги, SLA, 3 режима.
- [x] Tenant-изоляция подтверждена RLS + тестами.
- [x] Токены шифруются at-rest; SSRF закрыт.
- [x] Тесты voice E2E / injection / load / RAG eval зелёные.
- [x] `/readiness` честно показывает всех провайдеров.
- [x] Документация заполнена; `PRODUCTION_READINESS_REPORT.md` с реальными прогонами.

## Порядок исполнения

`T0.1 → T0.2 → T0.3 → T1.1 → T1.2 → T1.3 → T1.4 → T2.1 → T2.2 → T2.3 → T2.4 → T3.1 → T3.2 → T3.3 → T3.4 → T3.5 → T4.1 → T4.2 → T4.3`

После каждой фазы: полный прогон проверок + сводка в PR (что сделано, что в mock, что требует ключей).
