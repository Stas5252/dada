# Workspace Skills

## 1. premium-web-design-director
**Назначение:** делать сайты визуально дорогими, не generic.
**Workflow:**
- Сначала спросить/вывести brand hypothesis: audience, price point, trust signals, emotional tone.
- Определить art direction: typography, grid, spacing, color, surfaces, imagery, motion.
- Создать design tokens: colors, radius, shadows, spacing, typography.
- Создать UI audit checklist.
- Проверить каждый экран на hierarchy, contrast, rhythm, alignment, density, whitespace, responsiveness.
- Запретить generic AI look.

## 2. visual-qa-polisher
**Назначение:** доводить UI до pixel-level качества.
**Workflow:**
- Запустить dev server.
- Открыть страницу в браузере через Chrome DevTools или Playwright.
- Сделать screenshots desktop/tablet/mobile.
- Проверить console errors, network errors, layout shifts, overflowing text, broken states.
- Проверить hover/focus/active/loading/empty/error states.
- Проверить accessibility: labels, focus order, contrast, keyboard navigation.
- Составить punch list.
- Исправить проблемы.
- Повторить проверку до чистого результата.

## 3. finish-to-ship-engineer
**Назначение:** не бросать проект на 80%.
**Workflow:**
- Составить task list.
- Реализовать по одному slice.
- После каждого slice запускать релевантные проверки.
- Перед финалом обязательно: lint, typecheck, unit tests, e2e/smoke tests, build.
- Проверить env/example, README, setup instructions, deploy readiness.
- Проверить production risks: secrets, auth, payments, database migrations, rate limits, error handling, analytics, Sentry/logging.
- Итоговый ответ должен содержать: что сделано, какие команды прошли, какие файлы изменены, что осталось, как запустить.
