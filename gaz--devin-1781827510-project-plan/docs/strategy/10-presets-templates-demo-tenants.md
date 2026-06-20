# 10. Presets, templates and demo tenants

## Why presets matter

The product must not start from an empty screen. Customers should launch by choosing an industry preset, then editing it. This makes the platform feel finished and reduces implementation time.

Presets should cover:

- agent persona;
- tone of voice;
- allowed topics;
- escalation policy;
- knowledge templates;
- actions/tools;
- dashboard KPIs;
- demo conversations;
- golden test questions;
- sales demo data.

## Preset architecture

Each preset should become a versioned object in the repo and later in DB:

```yaml
preset_id: restaurant_delivery_ru_v1
industry: restaurant_delivery
language: ru
agent_persona: polite_operator
channels:
  - telegram
  - web_widget
  - voice
knowledge_templates:
  - menu
  - delivery_rules
  - payment_rules
  - refunds
procedures:
  - answer_menu_question
  - check_order_status
  - create_order_draft
  - escalate_complaint
integrations:
  - iiko
  - yookassa
  - telegram
metrics:
  - automation_rate
  - missed_leads
  - order_conversion
```

Future code location:

- `apps/api/app/presets/`
- `apps/api/app/seed/demo_tenants.py`
- `apps/web/app/templates/`

## Industry preset 1: restaurant and delivery

### Agent name examples

- “AI Оператор Доставки”
- “Restaurant Support RU”
- “AI Администратор ресторана”

### Primary jobs

- answer menu/ingredients/allergens questions;
- delivery zone/time/cost;
- order status;
- table booking;
- promo rules;
- complaints and refunds;
- operator handoff.

### Required knowledge templates

- `menu.md`: categories, dishes, prices, modifiers;
- `delivery.md`: zones, ETA, courier rules;
- `payments.md`: payment methods, refunds, receipts;
- `working-hours.md`: branch hours, holidays;
- `faq.md`: popular questions;
- `handoff-policy.md`: when to call operator.

### Required actions

- `iiko.menu.fetch`;
- `iiko.order.status`;
- `iiko.order.create_draft`;
- `yookassa.payment.create`;
- `operator.handoff`.

### Golden questions

- “Какая доставка до моего адреса?”
- “Есть ли пицца без глютена?”
- “Где мой заказ?”
- “Можно изменить заказ?”
- “Как вернуть деньги?”
- “Позовите оператора.”

### Demo KPIs

- automation rate target: 60–75%;
- p95 chat latency: < 2s;
- unresolved topics: < 10% after first tuning;
- order conversion uplift: measurable after integration.

## Industry preset 2: clinic and appointments

### Jobs

- answer service/pricing questions;
- collect lead name/phone/service;
- suggest appointment windows;
- explain preparation rules;
- route urgent medical issues to human;
- reminders.

### Knowledge templates

- services and prices;
- doctors/specialists;
- preparation instructions;
- contraindication disclaimer;
- appointment rules;
- privacy/consent text.

### Guardrails

- no diagnosis;
- no treatment recommendations;
- urgent symptoms -> emergency/human handoff;
- always clarify that information is administrative.

### Golden questions

- “Сколько стоит консультация?”
- “Как подготовиться к анализам?”
- “Можно записаться завтра?”
- “У меня острая боль, что делать?”

## Industry preset 3: e-commerce

### Jobs

- order status;
- delivery tracking;
- returns/exchanges;
- product availability;
- size guide;
- promo rules;
- complaint escalation.

### Integrations

- CRM/order system;
- delivery provider;
- payment provider;
- warehouse/catalog.

### Golden questions

- “Где мой заказ?”
- “Как оформить возврат?”
- “Есть размер M?”
- “Можно изменить адрес доставки?”

## Industry preset 4: service business

Examples: cleaning, repair, beauty, education, legal intake.

### Jobs

- qualify lead;
- estimate service category;
- collect contact;
- book consultation;
- answer FAQ;
- handoff complex request.

## Universal templates

### Agent persona template

Fields:

- name;
- business role;
- tone;
- target audience;
- forbidden claims;
- escalation triggers;
- confidence threshold;
- answer length rules;
- source citation rules.

### Handoff policy template

Escalate when:

- user asks for human;
- confidence is low;
- no source found;
- payment/order conflict;
- legal/medical/safety question;
- customer is angry;
- repeated failed answer.

Handoff payload:

- transcript;
- summary;
- detected intent;
- customer data;
- source IDs;
- actions attempted;
- recommended next action.

### Knowledge source checklist

Before launch:

- FAQ loaded;
- pricing/menu loaded;
- delivery/working rules loaded;
- refund/cancellation policy loaded;
- escalation contacts configured;
- at least 30 golden Q&A tested.

### Demo tenant data

Each demo tenant should have:

- tenant profile;
- two agents;
- 3–5 knowledge sources;
- 10–20 conversations;
- unresolved topics;
- billing usage examples;
- integration readiness states.

Current local seed creates `Demo Pizza` with fixed tenant id
`00000000-0000-0000-0000-000000000001`, two agents, two restaurant knowledge
sources and three conversations. It is implemented in `apps/api/app/demo_data.py`
and can be applied with `make seed-demo`.

## Product UI requirements for presets

- “Choose your industry” screen;
- preview what preset creates;
- one-click demo tenant creation;
- edit before publish;
- test questions generated from preset;
- checklist progress;
- reset/reseed demo option for sales demos.

## Implementation checklist

- [ ] Define preset schema.
- [ ] Store presets as YAML/JSON fixtures.
- [x] Add seed command for demo tenants.
- [ ] Add API: list presets, preview preset, apply preset.
- [ ] Add frontend preset chooser.
- [ ] Add generated knowledge templates.
- [ ] Add golden question runner per preset.
- [ ] Add sales demo tenant switcher.
