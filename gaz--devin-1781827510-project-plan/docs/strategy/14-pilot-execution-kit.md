# 14. Pilot execution kit

## Goal

Turn each pilot into a repeatable process that improves product, presets and sales materials.

## Pilot scope template

```text
Pilot duration: 14 days
Channels: Telegram and/or web widget
Industry preset: restaurant_delivery_ru_v1
Knowledge: menu, FAQ, delivery, payment/refund rules
Integrations: optional iiko/YooKassa sandbox or local stub
Success criteria: automation rate, latency, handoff quality, no critical hallucinations
Report: baseline, results, ROI, next steps
```

## Onboarding questionnaire

Business:

- company name;
- industry;
- locations;
- working hours;
- current support channels;
- daily/monthly support volume;
- current operator count/cost;
- top 20 repeated questions;
- systems used: iiko/CRM/payment/telephony.

Knowledge:

- menu/catalog;
- prices;
- delivery rules;
- refunds;
- contacts;
- escalation contacts;
- forbidden topics;
- brand tone.

Legal/ops:

- who approves answers;
- can calls be recorded;
- personal data policy exists;
- data retention expectations;
- channels allowed for notifications.

## Pilot setup checklist

- [ ] Tenant created.
- [ ] Industry preset applied.
- [ ] Agent persona confirmed.
- [ ] Knowledge uploaded.
- [ ] Golden questions loaded.
- [ ] Channel connected.
- [ ] Handoff operator configured.
- [ ] Readiness check reviewed.
- [ ] Baseline metrics captured.
- [ ] Launch time agreed.

## Daily pilot review

Check:

- failed answers;
- no-answer events;
- handoffs;
- unresolved topics;
- latency;
- customer complaints;
- integration failures;
- operator feedback.

Update:

- knowledge base;
- escalation rules;
- prompt/policy;
- golden questions;
- preset if reusable.

## Final pilot report template

Sections:

1. summary;
2. baseline support volume;
3. conversations processed;
4. automation rate;
5. no-answer/handoff stats;
6. top unresolved topics;
7. saved operator time;
8. revenue/order impact if measured;
9. incidents/risks;
10. recommendation: continue / expand / stop;
11. proposed subscription package.

## Customer success scripts

### Launch message

```text
Мы запустили AI-оператора в тестовом режиме. Первые дни смотрим качество ответов, собираем сложные вопросы и дообучаем базу знаний. Все спорные случаи будут уходить оператору.
```

### Weekly report summary

```text
За неделю AI обработал X диалогов, Y% закрыто без оператора, Z вопросов передано человеку. Основные темы для улучшения: A, B, C. Экономия по времени: примерно N часов.
```

## Pilot-to-paid close

Move to paid plan when:

- owner sees ROI;
- operator team trusts handoff;
- no critical hallucinations;
- integration/channel works reliably;
- next month scope is clear.

Offer:

- convert pilot setup into first month discount only if paid contract signed quickly;
- propose 3-month commitment for tuning;
- upsell integration/voice after chat proves value.
