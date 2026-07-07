# SECURITY.md — Безопасность CallForce

## Аутентификация

- JWT-токены (access + refresh) с `ACCESS_TOKEN_SECRET`
- Access-токен: 15 мин TTL (настраивается)
- Refresh-токен: 30 дней TTL, хэшируется в БД
- Регистрация с email-верификацией
- Пароли хэшируются через bcrypt

## Авторизация (RBAC)

4 роли с иерархией прав:
- **owner** — все права, включая управление пользователями
- **admin** — управление агентами, базой знаний, биллингом; НЕ может управлять auth
- **agent** — управление чатами, чтение агентов и базы знаний
- **viewer** — только чтение

## Мультитенантная изоляция

- Каждый запрос фильтруется по `tenant_id` из JWT
- Row-Level Security (RLS) на уровне PostgreSQL
- Тесты tenant isolation подтверждают, что тенант A не видит данные тенанта B

## Guard Rails (AI Safety)

- **Prompt injection detection**: 10+ паттернов на RU и EN
- **Toxicity detection**: автоматическая эскалация на оператора
- **Secret leak prevention**: блокировка системного промпта и ключей в ответах LLM
- **Prohibited claims**: блокировка необоснованных гарантий ("100% результат")
- **Opt-out/DNC**: автоматическая обработка запросов на отказ от коммуникаций
- **Human handoff**: автоматическая эскалация при запросе оператора

## SSRF Protection

- Валидация URL: запрет доступа к приватным IP-адресам
- Валидация при редиректах
- Ограничение размера загружаемого контента (5 MB)

## Шифрование

- Токены шифруются at-rest через Fernet
- `ACCESS_TOKEN_SECRET` обязательно должен быть изменён для production
- Все API-ключи интеграций хранятся только в переменных окружения

## Rate Limiting

- Глобальный rate limiter (настраивается через `RATE_LIMIT_ENABLED`)
- Per-endpoint лимиты на критичных эндпоинтах (auth, voice)

## Рекомендации для Production

1. Сменить `ACCESS_TOKEN_SECRET` на случайную строку ≥ 32 символа
2. Настроить HTTPS через reverse proxy (nginx/Caddy)
3. Настроить CORS origins (`CORS_ORIGINS`)
4. Включить Sentry (`SENTRY_DSN`)
5. Использовать PostgreSQL с SSL
6. Redis с паролем
