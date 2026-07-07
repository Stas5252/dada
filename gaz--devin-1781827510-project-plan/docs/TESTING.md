# TESTING.md — Стратегия тестирования CallForce

## Обзор

Проект использует `pytest` с `pytest-asyncio`. Все тесты запускаются через:

```bash
cd apps/api
.venv/Scripts/pytest -v
```

## Категории тестов

### Unit-тесты
- `test_vad.py` — Voice Activity Detection
- `test_parsers.py` — PDF/DOCX/URL парсинг
- `test_encryption.py` — Шифрование токенов
- `test_localization.py` — Нормализация телефонов РФ
- `test_llm_router.py` — Маршрутизация LLM

### Integration-тесты
- `test_core_mvp_flow.py` — Полный цикл: регистрация → агент → чат
- `test_sqlalchemy_store.py` — SqlAlchemy store CRUD
- `test_channels.py` — Webhook обработка (VK, WhatsApp)
- `test_webhooks.py` — Валидация вебхуков (YooKassa, Twilio, Telegram)
- `test_iiko_integration.py` — Интеграция с iikoCloud

### Voice E2E тесты
- `test_voice_e2e.py` — FSM голосовых сессий:
  - Входящий/исходящий звонок
  - Barge-in (перебивание)
  - Молчание → завершение
  - Злость → эскалация
  - Confirmation flow
  - Follow-up
  - Tenant isolation

### AI Safety / Guardrails
- `test_prompt_injection.py` — 32 теста:
  - Prompt injection (RU + EN)
  - Opt-out detection
  - Secret leak prevention
  - Prohibited claims
  - Human handoff intent
  - Toxicity escalation

### RBAC и Tenant Isolation
- `test_rbac_isolation.py` — Матрица ролей + межтенантная изоляция
- `test_auth_security.py` — Безопасность аутентификации
- `test_billing_limits.py` — Лимиты и биллинг

### RAG
- `test_rag.py` — Chunking, векторный поиск, confidence-gating
- `test_rag_eval.py` — RAG evaluation с golden-set
- `test_rag_ingestion.py` — Идемпотентный импорт источников

### Readiness
- `test_readiness_matrix.py` — Структура `/readiness`
- `test_integration_readiness.py` — Все провайдеры
- `test_health.py` — Health check

## Результаты последнего прогона

```
235 passed, 0 failed, 2 warnings
Время: ~75 секунд
```

## Что не покрыто (требует реальных ключей)

- Реальные вызовы OpenAI API → замокано через `LLMRouter`
- Реальные вызовы Yandex SpeechKit → замокано
- Реальные вызовы Twilio → замокано через `TwilioSimulator`
- Реальные вызовы YooKassa → замокано
- Load testing (k6/Locust) → отдельный запуск
