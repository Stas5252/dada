# 13. Pricing and unit economics

## Pricing principle

Price should be tied to value, not only model cost. Customers buy:

- faster response;
- fewer operator hours;
- fewer missed leads;
- more orders/bookings;
- better visibility and control.

## Starter pricing model

### Pilot

- 50k–150k ₽ one-time;
- 14 days;
- one channel;
- one industry preset;
- up to 1000 conversations;
- pilot report included.

### Starter

- 15k–49k ₽/month;
- Telegram or web widget;
- one agent;
- basic knowledge base;
- basic analytics;
- limited usage.

### Pro

- 50k–150k ₽/month;
- multiple channels;
- integrations;
- operator handoff;
- advanced analytics;
- priority support.

### Enterprise / networks

- 200k–800k+ ₽/month;
- multiple locations;
- SSO/RBAC;
- custom integrations;
- SLA;
- private deployment option;
- dedicated success manager.

## Usage pricing options

Choose one or combine:

1. per AI resolution: 3–15 ₽;
2. per conversation: 1–7 ₽;
3. per voice minute: 20–80 ₽;
4. included quota + overage;
5. flat subscription for SMB simplicity.

## Unit economics model

Track per tenant:

- LLM input/output tokens;
- embedding cost;
- STT/TTS cost;
- telephony minutes;
- infra cost;
- support/customer success time;
- gross margin.

Target:

- gross margin > 70% for chat;
- gross margin > 50–60% for voice early;
- payback period < 3 months for paid acquisition;
- implementation cost recovered by setup fee.

## ROI calculator formula

```text
monthly_savings = automated_conversations * avg_operator_minutes_saved * operator_minute_cost
extra_revenue = recovered_leads * conversion_rate * avg_order_value
platform_roi = monthly_savings + extra_revenue - monthly_fee
```

Example:

- 3000 support conversations/month;
- 60% automated;
- 4 minutes saved each;
- operator cost 12 ₽/minute;
- savings: 3000 * 0.6 * 4 * 12 = 86 400 ₽/month;
- subscription: 49 000 ₽/month;
- visible ROI before extra revenue.

## Packaging recommendations

For early sales, keep it simple:

- sell setup + monthly subscription;
- avoid complex per-message pricing until usage data exists;
- include fair usage cap;
- charge separately for custom integrations;
- charge voice separately because cost is higher.

## Pricing experiments

Test:

- 50k pilot vs free audit + paid setup;
- 29k/month starter vs 49k/month with more support;
- per-resolution bonus pricing;
- vertical-specific packages;
- partner commission included in price.

## What not to do early

- do not underprice custom integrations;
- do not promise unlimited voice usage;
- do not absorb large implementation effort without setup fee;
- do not sell enterprise custom features before core product is stable;
- do not process bank card data directly; use hosted payment pages.
