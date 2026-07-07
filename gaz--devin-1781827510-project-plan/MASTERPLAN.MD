<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>CallForce — IDEAL MASTER PLAN</title>
<style>
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; line-height: 1.55; max-width: 980px; margin: 40px auto; padding: 0 24px; color: #111827; }
h1, h2, h3 { line-height: 1.2; }
h1 { border-bottom: 3px solid #111827; padding-bottom: 12px; }
h2 { margin-top: 36px; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; }
table { border-collapse: collapse; width: 100%; margin: 16px 0; }
th, td { border: 1px solid #d1d5db; padding: 8px 10px; vertical-align: top; }
th { background: #f3f4f6; }
code, pre { background: #f3f4f6; border-radius: 6px; }
pre { padding: 12px; overflow-x: auto; }
blockquote { border-left: 4px solid #6366f1; padding-left: 16px; color: #374151; background: #f8fafc; }
</style>
</head>
<body>
<pre># CallForce — IDEAL MASTER PLAN  
## Полный production/enterprise blueprint для AI Voice + Omnichannel Sales &amp; Support Platform

**Дата версии:** 2026-07-07  
**Цель документа:** заменить разрозненные планы одним главным файлом для доведения CallForce до production-ready уровня.  
**Тип проекта:** B2B SaaS / AI Voice Agents / AI Support / AI Sales / Omnichannel CRM.  
**Главное правило:** галочка «готово» ставится только после теста, который доказывает работу функции. Если теста нет — функция не готова.

---

# 0. Главный вердикт

CallForce нельзя доводить до «идеала» как набор отдельных фич. Его нужно доводить как **систему**, где каждая часть связана с деньгами клиента:

**звонок / сообщение → AI понимает намерение → отвечает по базе знаний → квалифицирует → создаёт лид → передаёт человеку при риске → обновляет CRM → делает follow-up → считает результат → улучшает сценарии.**

Проект должен стать не «ботом» и не «генератором звонков», а:

## AI Revenue Operations Platform

Платформа для бизнеса, которая объединяет:

- AI-звонки;
- AI-сообщения;
- AI-продажи;
- AI-поддержку;
- AI-администратора;
- omnichannel inbox;
- CRM;
- аналитику;
- безопасность;
- compliance;
- биллинг;
- quality control;
- human handoff;
- отчёты по деньгам.

---

# 1. Текущий статус из исходного плана

Исходный документ фиксирует готовность примерно **55–60% до production** и указывает главный принцип: «готово» только после acceptance-теста. Также в исходном плане отмечены две критические красные зоны: **Voice** и **Security**.

Оценка из текущего файла:

| Слой | Статус | Что значит |
|---|---:|---|
| Auth + MFA / multi-tenant / RBAC | ~85% | крепкая база, но нужна гарантированная tenant isolation на уровне БД |
| Биллинг | ~70% | есть основа, нужны full test-mode, idempotency, лимиты, usage ledger |
| Оркестрация + tool registry + guardrails | ~65% | есть база, нужно усилить eval, safety, audit |
| Шаблоны агентов | ~70% | есть вертикали, нужны production сценарии и тесты |
| Каналы + inbox | ~60% | адаптеры есть, нужна единая модель, retry, signatures, dedup |
| RAG | ~55% | нужна RU-качество, citations, honest threshold, golden eval |
| CRM | ~40% | нужно довести сущности, pipeline, дедуп, связь с деньгами |
| Human handoff | ~50% | нужен SLA, очереди, режимы draft/auto/approval |
| Analytics | ~35% | нет weekly money report и executive dashboard |
| Voice | ~25% | нельзя считать готовым, пока нет streaming voice pipeline и voice E2E |
| Security | ~20% | главный blocker: RLS, encryption, SSRF, secrets, audit |

**Вывод:** текущий план правильный по направлению, но недостаточно полный для enterprise SaaS. Ниже — расширенная версия, где закрыты продукт, архитектура, безопасность, legal, тесты, SRE, продажи, поддержка, экономика и roadmap.

---

# 2. Главные принципы разработки

## 2.1. Нельзя строить «идеал» без фаз

Идеал достигается не количеством функций, а доказанной работоспособностью. Поэтому проект делится на уровни:

| Уровень | Назначение |
|---|---|
| **M0: Truth Baseline** | честный статус, тесты, readiness, безопасность |
| **M1: Paid Pilot** | текстовый AI-администратор + CRM + отчёт |
| **M2: Production v1** | voice inbound + omnichannel + handoff + billing |
| **M3: Scale** | outbound, кампании, аналитика, reliability, integrations |
| **M4: Enterprise** | SSO, SLA, audit, DPA, custom deployment, advanced governance |
| **M5: Platform/API** | публичный API, marketplace, partners, white-label |

## 2.2. Правило доказательства

Любая задача считается готовой только если есть:

1. код;
2. миграции, если нужна БД;
3. тесты;
4. документация;
5. observability;
6. security review;
7. acceptance criteria;
8. запись в readiness report;
9. отсутствие mock-only без явной пометки;
10. реальный прогон CI.

## 2.3. Запрет на самообман

Запрещено писать:

- «готово», если работает только mock;
- «production-ready», если не было load/security/e2e;
- «voice готов», если нет streaming, barge-in и voice E2E;
- «security готов», если токены лежат открыто;
- «multi-tenant готов», если нет теста на утечку tenant данных;
- «AI продаёт», если нет метрик конверсии;
- «лучше Bland AI», если нет latency, reliability и кейсов.

---

# 3. Продуктовая стратегия

## 3.1. Кто платит

Лучшие первые сегменты:

| Сегмент | Почему подходит | Риск |
|---|---|---|
| Автосервисы | звонки, запись, повторные клиенты, понятный чек | данные о расписании и услугах должны быть точными |
| Салоны красоты | запись, повторные визиты, Telegram/VK, простая база знаний | часто небольшой чек |
| Клининг | заявки, расчёт, районы, follow-up | конкуренция, сезонность |
| Ремонтные услуги | высокий чек, много звонков, срочность | часто хаотичный процесс |
| Онлайн-школы | лиды, дожим, follow-up, CRM | высокий churn, много конкурентов |
| Клиники/стоматологии | высокий чек | legal/compliance, медицинские ограничения |

**Лучший старт:** автосервис / салон / клининг.  
**Enterprise позже:** клиники, call-центры, банки, e-commerce.

## 3.2. Главная боль клиента

Не «у нас нет ИИ». Боль такая:

- не отвечают быстро;
- теряют звонки и сообщения;
- менеджеры забывают follow-up;
- лиды не попадают в CRM;
- нет понимания, откуда деньги;
- клиенты уходят после первого касания;
- владелец не видит, кто плохо работает;
- заявки дорогие, а обработка слабая.

## 3.3. Главный оффер

**CallForce — AI-администратор и AI-продавец, который отвечает клиентам 24/7, принимает звонки и сообщения, создаёт заявки в CRM, возвращает потерянных клиентов и показывает, где бизнес теряет деньги.**

---

# 4. Что должно быть лучше аналогов

## 4.1. Не копировать Bland AI один в один

Bland AI — сильная voice AI платформа. CallForce должен отличаться не только звонками, а связкой:

- voice + messaging;
- РФ/СНГ локализация;
- Telegram/VK/WhatsApp/WebChat;
- CRM-first;
- money analytics;
- human handoff;
- режимы draft/approval/autopilot;
- локальные провайдеры: Yandex SpeechKit, ЮKassa, GigaChat/YandexGPT;
- отчёт «сколько денег потеряно / восстановлено».

## 4.2. Killer features

1. **Lost Lead Recovery:** система находит пропущенные обращения и возвращает их.
2. **Money Report:** показывает потенциально потерянную выручку.
3. **AI Supervisor:** оценивает звонки и переписки.
4. **Unified Inbox:** все каналы в одном месте.
5. **Human Handoff:** AI не ломает сложные сделки.
6. **No-Hallucination Mode:** AI отвечает только из базы знаний по критичным вопросам.
7. **RU-first Voice:** русский язык, номера, адреса, юридика, локальные каналы.
8. **Autopilot Levels:** draft → approval → autopilot.
9. **Conversion QA:** не просто отвечает, а ведёт к заявке.
10. **Readiness Honesty:** клиент видит, что реально подключено, а что mock/test.

---

# 5. Архитектура высокого уровня

## 5.1. Рекомендуемый подход

До стабильного product-market fit не делать микросервисы. Использовать:

## Modular Monolith + Event Bus + Workers

Преимущества:

- быстрее разработка;
- проще транзакции;
- проще тестировать;
- дешевле поддержка;
- меньше DevOps-сложности;
- можно выделить микросервисы позже.

## 5.2. Основные слои

```
apps/
  web/                 # frontend
  api/                 # backend API
  workers/             # background jobs
  voice-gateway/       # realtime voice, если вынести отдельно

packages/
  shared-types/
  ui/
  sdk/
  prompts/
  providers/
  test-utils/

infra/
  docker/
  migrations/
  terraform/optional

docs/
  architecture/
  product/
  security/
  testing/
  runbooks/
```

## 5.3. Backend modules

| Модуль | Назначение |
|---|---|
| Auth | пользователи, сессии, MFA |
| Organizations | multi-tenant SaaS |
| RBAC | роли и права |
| Agents | конфиг AI-агентов |
| Knowledge | RAG, документы, chunking |
| Conversations | сообщения, статусы, история |
| Voice | звонки, поток, транскрипты |
| Channels | Telegram, VK, WhatsApp, webchat, email |
| CRM | лиды, сделки, задачи |
| Handoff | передача человеку |
| Campaigns | outbound/follow-up |
| Billing | тарифы, usage, платежи |
| Analytics | события, отчёты, money metrics |
| Compliance | consent, DNC, data retention |
| Security | audit, encryption, policies |
| Admin | системная панель |

## 5.4. Рекомендуемый стек

| Слой | Рекомендация |
|---|---|
| Frontend | Next.js + TypeScript |
| Backend | FastAPI или NestJS |
| Database | PostgreSQL |
| Tenant isolation | PostgreSQL RLS + middleware session variable |
| Queue | Redis + Arq/BullMQ |
| Vector DB | pgvector или Qdrant |
| Realtime | WebSocket |
| Voice framework | Pipecat или LiveKit Agents |
| Telephony | Twilio Media Streams / SIP provider abstraction |
| STT | Deepgram / Yandex SpeechKit / fallback faster-whisper |
| TTS | ElevenLabs / Cartesia / Yandex SpeechKit |
| LLM | OpenAI / Anthropic / YandexGPT / GigaChat / fallback |
| Observability | OpenTelemetry + Prometheus + Grafana + Sentry |
| Deployment | Docker + CI/CD |
| Storage | S3-compatible |
| Payments РФ | ЮKassa |

---

# 6. Data model

## 6.1. Базовые сущности

Обязательные таблицы:

- users;
- organizations;
- organization_members;
- roles;
- permissions;
- audit_logs;
- agents;
- agent_versions;
- agent_templates;
- knowledge_bases;
- knowledge_documents;
- knowledge_chunks;
- knowledge_sources;
- integrations;
- channels;
- conversations;
- messages;
- calls;
- call_segments;
- call_transcripts;
- contacts;
- leads;
- deals;
- pipelines;
- stages;
- tasks;
- notes;
- tags;
- handoff_events;
- campaigns;
- campaign_leads;
- followups;
- usage_records;
- subscriptions;
- invoices;
- payments;
- consent_records;
- do_not_call_entries;
- safety_incidents;
- ai_evaluations;
- reports;
- webhooks;
- webhook_deliveries;
- provider_events.

## 6.2. Tenant isolation

Каждая tenant-scoped таблица обязана иметь:

- `tenant_id`;
- индекс `(tenant_id, id)`;
- индексы `(tenant_id, created_at)`, `(tenant_id, status)`, если используются;
- RLS policy `USING` и `WITH CHECK`;
- тест, что другой tenant не видит данные.

## 6.3. Что шифровать

At-rest encryption:

- токены каналов;
- API keys;
- refresh tokens;
- access tokens;
- telephony secrets;
- payment secrets;
- webhook secrets;
- PII high-risk поля, если требуется.

## 6.4. Что маскировать в UI/API

- номера карт;
- токены;
- телефоны частично;
- email частично;
- ключи интеграций;
- webhooks secrets;
- transcript fragments с sensitive data.

---

# 7. Voice AI pipeline

## 7.1. Нельзя использовать `&lt;Gather&gt;` как production voice AI

`&lt;Gather&gt;` подходит для простых IVR-сценариев, но не для low-latency real-time AI разговора. Production voice требует streaming pipeline.

## 7.2. Целевая архитектура

```
Telephony Provider
  ↓ WebSocket/RTP audio stream
Voice Gateway
  ↓ VAD + turn detection
Streaming STT
  ↓ partial transcript
Conversation Orchestrator
  ↓ RAG + tools + policy
Streaming LLM
  ↓ partial response
Streaming TTS
  ↓ audio chunks
Telephony Provider
```

## 7.3. Latency budget

| Компонент | Цель |
|---|---:|
| VAD / endpointing | 100–250 ms |
| STT partial | 80–200 ms |
| LLM TTFT | 150–350 ms |
| RAG retrieval | 50–150 ms |
| Tool call simple | 100–500 ms |
| TTS first chunk | 80–250 ms |
| Network/audio buffer | 50–150 ms |
| **P50 time-to-first-audio** | **&lt; 900 ms** |
| **P95 time-to-first-audio** | **&lt; 1500 ms** |

## 7.4. Обязательные voice-функции

- inbound calls;
- outbound calls;
- streaming STT;
- streaming TTS;
- barge-in;
- silence detection;
- turn-taking;
- call recording;
- transcript;
- summary;
- outcome;
- call transfer;
- voicemail/AMD для outbound;
- fallback to human;
- provider failover;
- per-stage metrics;
- DNC/consent;
- call simulation mode.

## 7.5. Voice E2E scenarios

Voice нельзя считать готовым, пока не пройдены сценарии:

1. входящий звонок;
2. исходящий звонок;
3. клиент перебивает AI;
4. клиент молчит;
5. клиент злится;
6. клиент просит оператора;
7. клиент задаёт вопрос вне базы;
8. клиент хочет записаться;
9. клиент спрашивает цену;
10. клиент отказывается;
11. AI делает follow-up;
12. STT provider падает;
13. TTS provider падает;
14. LLM timeout;
15. transfer to human;
16. запись звонка сохраняется;
17. transcript создаётся;
18. CRM обновляется;
19. отчёт строится;
20. p50/p95 замерены.

---

# 8. AI Orchestrator

## 8.1. Роль оркестратора

AI Orchestrator не должен быть просто вызовом LLM. Он должен управлять:

- intent detection;
- RAG retrieval;
- tool calling;
- safety policies;
- handoff rules;
- memory;
- CRM actions;
- channel-specific behavior;
- latency;
- fallback;
- logging;
- evaluation.

## 8.2. Prompt architecture

Каждый AI-агент должен иметь:

- system prompt;
- business profile;
- role prompt;
- tone prompt;
- channel prompt;
- sales policy;
- support policy;
- compliance policy;
- forbidden claims;
- handoff policy;
- tool policy;
- no-hallucination policy;
- output format policy.

## 8.3. Tool registry

Обязательные tools:

- `search_knowledge_base`;
- `capture_lead`;
- `update_lead`;
- `create_deal`;
- `create_task`;
- `schedule_appointment`;
- `check_availability`;
- `calculate_estimate`;
- `transfer_to_human`;
- `send_followup`;
- `mark_do_not_call`;
- `create_support_ticket`;
- `log_safety_incident`;
- `summarize_conversation`;
- `score_lead`;
- `score_conversation_quality`.

## 8.4. Tool safety

Каждый tool должен иметь:

- JSON schema;
- input validation;
- permission check;
- tenant check;
- idempotency key;
- audit log;
- rate limit;
- rollback/compensation, где нужно;
- test coverage.

## 8.5. No-hallucination режим

Критичные темы:

- цены;
- скидки;
- наличие услуги;
- гарантия;
- сроки;
- медицинские советы;
- юридические советы;
- финансовые обещания;
- политика возврата;
- запись;
- условия договора.

Правило: если нет данных в базе знаний — AI не выдумывает, а говорит:

&gt; “У меня нет точной информации по этому вопросу. Я передам обращение специалисту.”

---

# 9. RAG / Knowledge Base

## 9.1. Источники знаний

- ручной FAQ;
- услуги и цены;
- сайт клиента;
- PDF;
- DOCX;
- XLSX;
- CSV;
- TXT;
- HTML;
- CRM notes;
- previous resolved conversations;
- call summaries;
- policies;
- scripts;
- objections;
- legal disclaimers.

## 9.2. Pipeline

1. Ingestion.
2. Virus/file type validation.
3. Text extraction.
4. Language detection.
5. Cleanup.
6. Chunking with overlap.
7. Metadata.
8. Embeddings.
9. Vector storage.
10. Reranking.
11. Citation mapping.
12. Eval.
13. Versioning.
14. Re-index.
15. Rollback.

## 9.3. RU quality

Для РФ обязательно:

- RU embeddings;
- RU reranker;
- RU eval set;
- морфология русского языка;
- смешанные запросы RU/EN;
- телефоны РФ;
- адреса РФ;
- локальные термины ниш.

## 9.4. RAG acceptance tests

- RU query finds RU chunk;
- out-of-scope question triggers no-answer;
- price question without source escalates;
- answer includes source IDs;
- recall@5 &gt; 0.8 on golden set;
- hallucination rate below threshold;
- prompt injection in uploaded document does not override system prompt.

---

# 10. Omnichannel messaging

## 10.1. Каналы

Приоритет:

1. WebChat.
2. Telegram.
3. VK.
4. WhatsApp Business API.
5. Email.
6. Generic webhook.
7. Avito, если доступно официально.
8. Instagram/Facebook, если разрешено правилами и API.

## 10.2. Единая модель

Все каналы приводятся к сущностям:

- Channel;
- Conversation;
- Message;
- Contact;
- Attachment;
- DeliveryStatus;
- HandoffState;
- Source;
- ExternalThreadId.

## 10.3. Обязательные свойства адаптеров

Каждый адаптер должен иметь:

- inbound webhook;
- outbound sender;
- signature verification;
- retry;
- dedup;
- rate limits;
- delivery logs;
- provider error mapping;
- test mode;
- mock mode;
- health check;
- reconnect strategy;
- documentation.

## 10.4. Режимы AI

- **Draft:** AI пишет черновик, человек отправляет.
- **Approval:** AI отвечает после подтверждения.
- **Autopilot:** AI отвечает сам в рамках политики.
- **Restricted Autopilot:** AI отвечает только на FAQ, остальное эскалирует.

---

# 11. CRM and revenue system

## 11.1. CRM должна быть ядром, не дополнением

Если AI отвечает, но не создаёт лид — продукт не связан с деньгами.

Обязательная цепочка:

```
Conversation/Call → Contact → Lead → Deal → Task → Outcome → Revenue attribution
```

## 11.2. Lead fields

- name;
- phone;
- email;
- channel;
- source;
- UTM;
- service interest;
- budget;
- urgency;
- quality;
- temperature;
- status;
- reject reason;
- manager owner;
- created by AI / human;
- conversation ID;
- call ID;
- estimated value;
- actual revenue;
- next follow-up date;
- consent flags.

## 11.3. Дедупликация

Дедуп по:

- phone normalized;
- email normalized;
- external user id;
- channel id;
- fuzzy name + phone;
- recent duplicate window.

## 11.4. Pipeline

Минимальная воронка:

1. New.
2. Qualified.
3. Contacted.
4. Appointment booked.
5. Won.
6. Lost.
7. No response.
8. Do not contact.

---

# 12. Human handoff

## 12.1. Когда AI обязан передать человеку

- пользователь просит человека;
- злость/конфликт;
- низкая уверенность;
- вопрос вне базы;
- юридический/медицинский/финансовый риск;
- высокая сумма сделки;
- жалоба;
- возврат денег;
- персональные данные;
- нестандартная скидка;
- техническая ошибка;
- AI уже дважды не смог ответить.

## 12.2. Inbox

Обязательные функции:

- очередь;
- назначение менеджеру;
- теги;
- приоритеты;
- заметки;
- внутренние комментарии;
- SLA timer;
- статус диалога;
- история AI действий;
- кнопка “забрать диалог”;
- кнопка “вернуть AI”;
- summary перед передачей;
- уведомления.

---

# 13. Campaigns and follow-up

## 13.1. Outbound нельзя делать без compliance

Outbound должен уважать:

- consent;
- DNC;
- рабочие часы;
- лимиты частоты;
- правила платформ;
- антиспам;
- отказ пользователя;
- статус лида;
- legal category.

## 13.2. Campaign fields

- name;
- objective;
- script;
- audience;
- leads;
- variables;
- schedule;
- max attempts;
- retry delay;
- stop rules;
- success criteria;
- fail criteria;
- channel;
- budget/limits;
- compliance mode.

## 13.3. Follow-up examples

- после пропущенного звонка;
- после незавершённого диалога;
- после “я подумаю”;
- после записи;
- после неявки;
- после оказания услуги;
- просьба оставить отзыв;
- повторная продажа.

---

# 14. Analytics and AI Supervisor

## 14.1. Dashboard

Должен показывать:

- обращения;
- лиды;
- квалифицированные лиды;
- продажи;
- конверсию;
- скорость ответа;
- пропущенные обращения;
- восстановленные заявки;
- стоимость лида;
- стоимость минуты;
- маржу по клиенту;
- call outcomes;
- message outcomes;
- частые вопросы;
- частые возражения;
- причины отказов;
- качество AI;
- качество менеджеров;
- handoff rate;
- hallucination incidents;
- lost revenue estimate;
- recovered revenue estimate.

## 14.2. Weekly AI Growth Report

Каждую неделю система должна писать:

1. Что произошло.
2. Сколько обращений.
3. Сколько лидов.
4. Сколько продаж.
5. Где потеряли деньги.
6. Какие каналы сработали.
7. Какие вопросы повторяются.
8. Какие сценарии надо улучшить.
9. Какие менеджеры отвечали медленно.
10. Что сделать на следующей неделе.

## 14.3. AI Supervisor

Оценивает каждый диалог:

- factuality;
- tone;
- goal completion;
- lead qualification;
- sales quality;
- compliance risk;
- handoff correctness;
- customer sentiment;
- next best action.

---

# 15. Billing and unit economics

## 15.1. Биллинг должен считать usage

Обязательные usage records:

- AI messages;
- voice minutes;
- STT seconds;
- TTS characters;
- LLM tokens;
- knowledge storage;
- number of agents;
- number of seats;
- number of channels;
- outbound attempts;
- webhooks;
- reports.

## 15.2. Тарифы

| Тариф | Для кого | Что входит |
|---|---|---|
| Starter | малый бизнес | 1 агент, 1–2 канала, лимит сообщений |
| Growth | растущий бизнес | несколько агентов, CRM, inbox, аналитика |
| Pro | активные продажи | voice, outbound, follow-up, integrations |
| Enterprise | сети/call-centers | SLA, SSO, DPA, custom deployment |

## 15.3. Главные риски экономики

- стоимость минуты съедает маржу;
- клиенты создают длинные диалоги;
- AI отвечает слишком многословно;
- TTS дорогой;
- LLM fallback дорогой;
- саппорт дороже подписки;
- onboarding требует слишком много ручной работы.

## 15.4. Обязательные лимиты

- max calls/day;
- max outbound attempts;
- max conversation length;
- max tokens per response;
- max documents;
- max channels;
- max users;
- max storage;
- max retries.

---

# 16. Security

## 16.1. Production blockers

Без этого нельзя выпускать production:

- RLS;
- encrypted integration tokens;
- SSRF protection;
- webhook signatures;
- RBAC enforced;
- audit logs;
- rate limits;
- secure headers;
- CORS allowlist;
- dependency scan;
- SAST;
- tenant isolation tests;
- no secrets in logs;
- backups;
- incident runbook.

## 16.2. AI security

Нужно тестировать:

- prompt injection;
- data exfiltration;
- malicious uploaded docs;
- tool abuse;
- fake customer instructions;
- jailbreak;
- tenant data leakage;
- hallucinated prices;
- hallucinated policies;
- unauthorized CRM action.

## 16.3. Минимальный security checklist

- password hashing;
- MFA;
- session rotation;
- API key scopes;
- token encryption;
- audit logs;
- IP/rate limits;
- file upload scanning;
- MIME validation;
- size limits;
- private network blocking;
- secure logging;
- backups;
- restore testing.

---

# 17. Compliance / Legal / РФ

## 17.1. Персональные данные

Нужно продумать:

- кто оператор ПДн;
- кто обработчик;
- согласия;
- политика обработки данных;
- хранение;
- удаление;
- экспорт;
- доступ сотрудников;
- журнал действий;
- трансграничная передача, если используется иностранный провайдер;
- договоры с клиентами;
- DPA.

## 17.2. Запись звонков

Обязательно:

- настройка уведомления о записи;
- хранение записи;
- срок хранения;
- доступы;
- удаление;
- маскирование чувствительных данных;
- запрет использования записи вне цели.

## 17.3. Outbound и антиспам

Нужно:

- consent first;
- do-not-call;
- opt-out;
- частотные лимиты;
- stop words;
- лог согласия;
- запрет массовых рекламных обзвонов без правового основания;
- ручное подтверждение опасных кампаний.

## 17.4. Реклама

Если платформа помогает с рекламой:

- маркировка;
- erid;
- ОРД/ЕРИР;
- хранение данных рекламодателя;
- шаблоны ответственности;
- не запускать рекламу без подтверждения клиента.

## 17.5. Высокорисковые ниши

Для этих ниш нужен restricted mode:

- медицина;
- финансы;
- юристы;
- образование;
- недвижимость;
- трудоустройство;
- кредиты;
- страхование;
- БАДы.

---

# 18. Observability and reliability

## 18.1. Метрики

Обязательные:

- API latency;
- error rate;
- queue depth;
- webhook failures;
- provider failures;
- STT latency;
- LLM latency;
- TTS latency;
- voice TTFA;
- call drop rate;
- message delivery failures;
- handoff rate;
- fallback rate;
- hallucination incidents;
- cost per org;
- margin per org.

## 18.2. Logs

Нужны structured logs:

- request id;
- tenant id;
- user id;
- agent id;
- conversation id;
- provider;
- latency;
- error code;
- tool call;
- safety event.

Не логировать:

- raw tokens;
- API keys;
- full passwords;
- sensitive PII без необходимости.

## 18.3. Runbooks

Создать:

- provider outage;
- high latency;
- voice degradation;
- data leak suspicion;
- payment outage;
- webhook storm;
- queue stuck;
- high hallucination rate;
- production rollback;
- backup restore.

---

# 19. Testing strategy

## 19.1. Типы тестов

| Тип | Что проверяет |
|---|---|
| Unit | логика модулей |
| Integration | БД, providers, tools |
| API | контракты |
| E2E | user journey |
| Voice E2E | звонки, barge-in, latency |
| Security | RLS, SSRF, prompt injection |
| Load | нагрузка |
| Billing | usage, лимиты, idempotency |
| RAG eval | качество ответов |
| UX | mobile, accessibility |
| Recovery | рестарт, retry, backup |

## 19.2. Must-pass сценарии

1. Регистрация → организация → агент.
2. Агент получает базу знаний.
3. WebChat задаёт вопрос.
4. AI отвечает с источником.
5. AI создаёт лид.
6. Менеджер забирает диалог.
7. AI возвращает диалог после handoff.
8. Telegram сообщение создаёт conversation.
9. Повторный контакт не создаёт дубль.
10. Голосовой звонок симулируется.
11. Barge-in работает.
12. Outbound уважает DNC.
13. Billing блокирует лимит.
14. Другой tenant не видит данные.
15. Prompt injection не срабатывает.
16. SSRF блокируется.
17. Weekly report создаётся.
18. CI падает, если галочка без теста.

---

# 20. Documentation

Обязательные файлы:

- `README.md`;
- `AGENTS.md`;
- `FINISH_PROJECT_v3_IDEAL.md`;
- `docs/PROJECT_AUDIT.md`;
- `docs/ARCHITECTURE.md`;
- `docs/PRODUCT.md`;
- `docs/API.md`;
- `docs/ENVIRONMENT.md`;
- `docs/DEPLOYMENT.md`;
- `docs/SECURITY.md`;
- `docs/TESTING.md`;
- `docs/COMPLIANCE.md`;
- `docs/VOICE_PIPELINE.md`;
- `docs/RAG_EVAL.md`;
- `docs/BILLING.md`;
- `docs/RUNBOOKS.md`;
- `docs/COMPETITOR_BENCHMARK.md`;
- `docs/PRODUCTION_READINESS_REPORT.md`.

---

# 21. Production readiness gates

## Gate 0 — Truth

- readiness отражает код;
- fake checkboxes удалены;
- все mock-only явно помечены;
- CI есть.

## Gate 1 — Security

- RLS;
- encryption;
- SSRF;
- secrets;
- audit;
- tenant tests.

## Gate 2 — Core product

- agent builder;
- knowledge base;
- webchat;
- Telegram;
- CRM lead creation;
- inbox;
- handoff.

## Gate 3 — Voice

- streaming pipeline;
- STT/LLM/TTS;
- barge-in;
- transfer;
- transcripts;
- voice E2E;
- latency metrics.

## Gate 4 — Revenue

- billing;
- usage;
- limits;
- CRM;
- analytics;
- weekly money report.

## Gate 5 — Scale

- queues;
- retries;
- load tests;
- monitoring;
- runbooks.

## Gate 6 — Enterprise

- SSO;
- SLA;
- DPA;
- advanced audit;
- custom deployment;
- admin controls.

---

# 22. Расширенный backlog

## A. Truth + Security

- A1. Синхронизировать readiness с кодом.
- A2. Включить RLS для всех tenant tables.
- A3. Зашифровать integration tokens.
- A4. Реализовать SSRF protection.
- A5. Исправить типы и схемы безопасности.
- A6. Добавить audit logs на все критичные действия.
- A7. Добавить secrets scanner в CI.
- A8. Добавить dependency scan.
- A9. Добавить rate limiting.
- A10. Добавить tenant-isolation test suite.

## B. RAG

- B1. RU embeddings.
- B2. Honest reranker threshold.
- B3. Chunk overlap.
- B4. Citations.
- B5. Golden set.
- B6. Prompt injection tests.
- B7. Document versioning.
- B8. Source confidence UI.
- B9. No-answer policy.
- B10. Knowledge approval workflow.

## C. CRM + Revenue

- C1. Полная CRM schema.
- C2. Auto lead capture.
- C3. Dedup.
- C4. Pipeline.
- C5. Tasks.
- C6. CSV import/export.
- C7. Webhook API.
- C8. Bitrix24/amo adapters.
- C9. Revenue attribution.
- C10. Lost lead estimate.

## D. Voice

- D1. Pipecat/LiveKit каркас.
- D2. TelephonyProvider interface.
- D3. Twilio Media Streams adapter.
- D4. SIP/Asterisk adapter позже.
- D5. Streaming STT.
- D6. VAD/turn-taking.
- D7. Barge-in.
- D8. Streaming LLM/TTS.
- D9. Call transfer.
- D10. Recording/transcript/summary.
- D11. Voice metrics.
- D12. Voice E2E.
- D13. Provider failover.
- D14. Call simulator.
- D15. Outbound call scheduler.

## E. Omnichannel

- E1. Unified model.
- E2. Webchat production.
- E3. Telegram production.
- E4. VK adapter.
- E5. WhatsApp adapter.
- E6. Email adapter.
- E7. Generic webhook.
- E8. Signature verification.
- E9. Retry/dedup.
- E10. Attachment handling.

## F. Handoff

- F1. Inbox.
- F2. Assignment.
- F3. SLA.
- F4. Notes/tags.
- F5. AI summary.
- F6. Draft/approval/autopilot.
- F7. Manager notifications.
- F8. Supervisor review queue.

## G. Campaigns

- G1. Durable queues.
- G2. Follow-up engine.
- G3. Campaign model.
- G4. CSV upload.
- G5. DNC/consent.
- G6. Schedule.
- G7. Attempt logic.
- G8. Stop rules.
- G9. Campaign report.

## H. Analytics

- H1. Event tracking.
- H2. Dashboard.
- H3. Channel conversion.
- H4. AI quality.
- H5. Manager quality.
- H6. Weekly report.
- H7. Cost/margin.
- H8. Revenue attribution.
- H9. Alerts.
- H10. Export.

## I. RU localization

- I1. RU prompts.
- I2. Yandex SpeechKit provider.
- I3. YandexGPT provider.
- I4. GigaChat provider.
- I5. ЮKassa end-to-end.
- I6. Phone normalization RU.
- I7. Address normalization RU.
- I8. 152-ФЗ templates.
- I9. Ad marking checklist.
- I10. Russian UI copy.

## J. Billing

- J1. Plans.
- J2. Usage ledger.
- J3. Limits.
- J4. Invoices.
- J5. Payment webhooks.
- J6. Idempotency.
- J7. Refunds.
- J8. Trial.
- J9. Grace period.
- J10. Cost dashboard.

## K. DevOps

- K1. Docker.
- K2. CI.
- K3. Migrations.
- K4. Seed/demo data.
- K5. Staging.
- K6. Production deploy.
- K7. Backups.
- K8. Restore test.
- K9. Observability.
- K10. Runbooks.

## L. Docs

- L1. README.
- L2. Architecture.
- L3. API.
- L4. Env.
- L5. Deployment.
- L6. Security.
- L7. Testing.
- L8. Compliance.
- L9. Voice.
- L10. Readiness.

---

# 23. Acceptance criteria template

Каждая задача должна иметь:

```md
## Task ID
Цель:

## Scope
Что входит:

## Out of scope
Что не входит:

## Implementation
Файлы/модули:

## Tests
Unit:
Integration:
E2E:
Security:
Load:

## Acceptance
- [ ] критерий 1
- [ ] критерий 2
- [ ] критерий 3

## Readiness
READY / MOCK_ONLY / REQUIRES_CREDENTIALS / BLOCKED

## Evidence
Команды:
Логи:
Скриншоты:
Ссылки:
```

---

# 24. AGENTS.md для AI coding agents

Добавить в репозиторий:

```md
# AGENTS.md

Ты работаешь над CallForce. Это production SaaS для AI voice + omnichannel sales/support.

Правила:
1. Не ставь готово без теста.
2. Один PR = одна задача.
3. Всегда запускай lint/typecheck/test/build.
4. Никогда не коммить секреты.
5. Все tenant-запросы фильтруй по tenant_id.
6. Все интеграционные токены шифруй.
7. Любой внешний URL проходит SSRF guard.
8. Все webhooks проверяют подпись.
9. Если нет credentials — делай provider interface + mock + env.example.
10. Voice готов только после voice E2E и latency metrics.
11. AI не должен выдумывать цены, гарантии, сроки, юридические/медицинские утверждения.
12. При низкой уверенности — handoff.
13. Обновляй docs и readiness после каждого изменения.
```

---

# 25. First 30 days

Цель: убрать самообман, закрыть security, доказать core value без тяжёлого enterprise.

## Неделя 1

- readiness truth;
- CI;
- RLS;
- token encryption;
- SSRF;
- audit logs.

## Неделя 2

- RAG RU;
- citations;
- no-answer;
- golden eval;
- webchat/Telegram production path.

## Неделя 3

- CRM lead capture;
- dedup;
- inbox;
- handoff;
- basic analytics.

## Неделя 4

- 3 пилота;
- weekly report;
- feedback loop;
- billing test-mode;
- production readiness report v1.

---

# 26. First 90 days

Цель: перейти от chat AI к voice + revenue platform.

- voice framework;
- streaming STT/TTS;
- barge-in;
- voice E2E;
- call transcript/summary;
- outbound follow-up;
- campaigns;
- VK/WhatsApp adapters;
- usage billing;
- margin dashboard;
- case studies;
- 10 платящих клиентов.

---

# 27. Что нельзя делать

- Не строить все каналы сразу.
- Не строить микросервисы до PMF.
- Не обещать 100% замену человека.
- Не запускать outbound без consent/DNC.
- Не хранить токены открыто.
- Не считать mock production.
- Не делать voice без streaming.
- Не игнорировать себестоимость минуты.
- Не заходить сразу в медицину/финансы без compliance.
- Не продавать как «бот». Продавать как «система заявок и продаж».

---

# 28. Final Definition of Done

CallForce можно считать production-ready, если:

- [ ] приложение запускается локально и на staging;
- [ ] CI зелёный;
- [ ] все critical tests зелёные;
- [ ] RLS включён;
- [ ] токены шифруются;
- [ ] SSRF закрыт;
- [ ] webhooks защищены;
- [ ] есть agent builder;
- [ ] есть knowledge base;
- [ ] есть RAG eval;
- [ ] есть webchat;
- [ ] есть Telegram;
- [ ] есть CRM;
- [ ] лид создаётся автоматически;
- [ ] есть dedup;
- [ ] есть inbox;
- [ ] есть handoff;
- [ ] есть voice streaming;
- [ ] есть barge-in;
- [ ] есть voice E2E;
- [ ] есть latency metrics;
- [ ] есть billing usage;
- [ ] есть limits;
- [ ] есть analytics dashboard;
- [ ] есть weekly money report;
- [ ] есть audit logs;
- [ ] есть docs;
- [ ] есть runbooks;
- [ ] есть production readiness report;
- [ ] все mock-only помечены;
- [ ] всё, что требует credentials, явно указано;
- [ ] нет критических security findings;
- [ ] есть первые реальные пилоты/кейсы.

---

# 29. Источники и технические ориентиры

Использовать как ориентиры при проектировании:

- Bland AI — enterprise voice AI platform, inbound/outbound AI phone agents, API, tools, conversation pathways.
- Twilio Media Streams — bidirectional WebSocket streams for real-time voice apps.
- Pipecat — framework for real-time voice and multimodal AI agents.
- LiveKit Agents — framework/platform for production voice AI agents.
- Telegram Bot API — official HTTP API for Telegram bots.
- WhatsApp Business Platform Cloud API — messaging/calling APIs for WhatsApp Business.
- Yandex SpeechKit — STT/TTS for RU-first voice.
- Роскомнадзор — уведомления по обработке персональных данных и рекомендации по маркировке интернет-рекламы.
- ЮKassa API — платежи, idempotency, webhooks.

---

# 30. Финальный порядок исполнения

```
A Truth/Security
→ B RAG
→ C CRM/Revenue
→ D Core channels
→ E Handoff
→ F Voice
→ G Billing
→ H Campaigns
→ I Analytics
→ J RU localization
→ K DevOps/Observability
→ L Docs/Readiness
→ M Paid pilots
→ N Production launch
→ O Scale/Enterprise
```

После каждой фазы:

1. полный прогон тестов;
2. обновление readiness;
3. обновление docs;
4. список mock/credentials;
5. список рисков;
6. решение: go / no-go.

---

# 31. Главная формула успеха

CallForce станет большим проектом не тогда, когда в нём будет «всё», а когда он стабильно докажет клиенту:

&gt; “Мы приняли обращения, вернули потерянные заявки, создали лиды, помогли менеджерам быстрее ответить и показали, сколько денег это принесло или спасло.”

Это и есть продукт. Всё остальное — инфраструктура вокруг этой ценности.
</pre>
</body>
</html>