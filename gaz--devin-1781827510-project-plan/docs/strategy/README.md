# Стратегия доведения Gaz AI Support Platform до идеальной рабочей системы

Этот раздел — не просто MVP roadmap. Это GitHub-ready план, по которому продукт нужно довести до уровня лучших AI support платформ рынка и адаптировать под российский рынок, законы, продажи и эксплуатацию.

## Главная цель

Сделать российскую omnichannel AI-платформу поддержки, которая:

- отвечает в чате и голосе на уровне Intercom Fin / Zendesk AI / Sierra / Ada;
- работает с российскими интеграциями: Telegram, сайт-виджет, SIP/Asterisk, iiko, ЮKassa, CRM/ERP;
- безопасно обрабатывает персональные данные по требованиям РФ;
- продается как понятный B2B SaaS с измеримым ROI: меньше обращений операторов, быстрее ответы, больше заказов;
- имеет production-grade backend, frontend, RAG, observability, тесты, CI/CD, support playbooks и customer success.

## Документы стратегии

1. [`01-market-benchmark.md`](01-market-benchmark.md) — ориентиры рынка и что нужно сделать лучше.
2. [`02-product-vision-and-positioning.md`](02-product-vision-and-positioning.md) — продуктовая стратегия, ICP, позиционирование.
3. [`03-target-customers-sales-funnel.md`](03-target-customers-sales-funnel.md) — как продавать продукт, воронка, офферы, demo flow.
4. [`04-production-architecture-roadmap.md`](04-production-architecture-roadmap.md) — целевая архитектура production-системы.
5. [`05-backend-plan.md`](05-backend-plan.md) — backend roadmap до production.
6. [`06-frontend-design-plan.md`](06-frontend-design-plan.md) — frontend, UX/UI, дизайн-система и onboarding.
7. [`07-qa-security-compliance-rf.md`](07-qa-security-compliance-rf.md) — тесты, безопасность, 152-ФЗ, локализация данных, платежи.
8. [`08-operations-launch-success-metrics.md`](08-operations-launch-success-metrics.md) — DevOps, support ops, аналитика, метрики запуска.
9. [`09-master-checklist.md`](09-master-checklist.md) — единый checklist “до идеала”.
10. [`10-presets-templates-demo-tenants.md`](10-presets-templates-demo-tenants.md) — industry presets, templates, demo tenants.
11. [`11-growth-marketing-playbook.md`](11-growth-marketing-playbook.md) — продвижение, growth, sales scripts.
12. [`12-product-convenience-and-gap-analysis.md`](12-product-convenience-and-gap-analysis.md) — удобство продукта и gap analysis.
13. [`13-pricing-unit-economics.md`](13-pricing-unit-economics.md) — цены, пакеты, unit economics.
14. [`14-pilot-execution-kit.md`](14-pilot-execution-kit.md) — процесс пилота и customer success templates.
15. [`15-final-gaps-and-risk-register.md`](15-final-gaps-and-risk-register.md) — risk register, pre-production checklists.
16. [`16-detailed-economics.md`](16-detailed-economics.md) — детальная экономика, P&L, breakeven, инвестиции.
17. [`17-real-cost-calculation.md`](17-real-cost-calculation.md) — реальный расчет при 0 ₽ вложений, API vs local GPU, цена звонка/диалога.
18. [`18-competitor-feature-benchmark-2026-06-20.md`](18-competitor-feature-benchmark-2026-06-20.md) — официальный benchmark Intercom/Fin, Zendesk, Ada, PolyAI, Retell, Bland/Five9 и честные parity gaps.
19. [`19-bland-parity-gap-and-next-steps-2026-06-21.md`](19-bland-parity-gap-and-next-steps-2026-06-21.md) — текущая сверка с Bland.ai, проверенные quality gates, честные gaps и порядок следующих slice.

## Связанные документы репозитория

- [`../../PROJECT_COMPLETION_PLAN.md`](../../PROJECT_COMPLETION_PLAN.md) — рабочий инженерный план и текущий статус.
- [`../../README.md`](../../README.md) — запуск и структура проекта.
- [`../architecture/overview.md`](../architecture/overview.md) — архитектурный обзор.
- [`../runbooks/local-development.md`](../runbooks/local-development.md)
- [`../runbooks/production-services.md`](../runbooks/production-services.md)
- [`../runbooks/rag-ingestion.md`](../runbooks/rag-ingestion.md)
- [`../runbooks/migration-dry-run.md`](../runbooks/migration-dry-run.md)
- [`../runbooks/smoke-checks.md`](../runbooks/smoke-checks.md)
- [`../runbooks/backup-restore-drill.md`](../runbooks/backup-restore-drill.md)

## Принцип выполнения

Каждый пункт в стратегии должен превращаться в issue/PR с:

- описанием user/business value;
- acceptance criteria;
- тестами;
- security/compliance проверкой;
- документацией и runbook;
- метрикой успеха.
