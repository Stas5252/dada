# 16. Detailed economics and financial model

## Purpose

Break down real costs, revenue expectations, and breakeven for the AI operator platform. All numbers are estimates for planning; actual costs depend on usage patterns, provider pricing, and scale.

---

## Cost categories

### 1. Infrastructure (monthly, for 1–10 tenants)

| Item | Provider options | Estimated cost |
|------|-----------------|----------------|
| PostgreSQL managed | Timeweb Cloud / Selectel / Yandex Cloud | 2 000–8 000 ₽/month |
| Qdrant (vector DB) | Self-hosted on VPS or Qdrant Cloud | 3 000–10 000 ₽/month |
| Redis | Managed or self-hosted | 1 000–3 000 ₽/month |
| Object storage (S3) | Selectel / Yandex / MinIO on VPS | 500–2 000 ₽/month |
| Application server (API + workers) | 2–4 vCPU, 4–8 GB RAM VPS | 3 000–8 000 ₽/month |
| Frontend hosting | Vercel / VPS / CDN | 0–3 000 ₽/month |
| Domain + SSL | — | 1 000–2 000 ₽/year |
| Monitoring (Grafana/Sentry) | Self-hosted or free tier | 0–3 000 ₽/month |
| **Total infra (early)** | | **10 000–35 000 ₽/month** |

### 2. LLM API costs (per conversation)

| Model | Input cost | Output cost | Avg conversation (2000 in + 500 out tokens) |
|-------|-----------|-------------|----------------------------------------------|
| GPT-4o-mini | $0.15/1M in, $0.60/1M out | | ~$0.0006 ≈ 0.06 ₽ |
| GPT-4o | $2.50/1M in, $10/1M out | | ~$0.01 ≈ 1 ₽ |
| Claude 3.5 Sonnet | $3/1M in, $15/1M out | | ~$0.014 ≈ 1.4 ₽ |
| Claude 3.5 Haiku | $0.80/1M in, $4/1M out | | ~$0.004 ≈ 0.4 ₽ |
| GigaChat (Sber) | ~2 ₽/1000 tokens | | ~5–8 ₽ per conversation |
| YandexGPT | ~1.2 ₽/1000 tokens | | ~3–5 ₽ per conversation |
| Local 8B (self-hosted GPU) | GPU rent 15 000–40 000 ₽/month | | amortized 0.5–2 ₽ at volume |

**Typical per-conversation LLM cost (using GPT-4o-mini + RAG context):** 0.5–3 ₽.

**With multi-turn (3–5 messages):** 2–10 ₽ per full conversation.

### 3. Embedding costs

| Provider | Cost |
|----------|------|
| OpenAI text-embedding-3-small | $0.02/1M tokens ≈ negligible |
| Local embedding model | included in server cost |

Embedding is cheap — typically < 0.01 ₽ per query.

### 4. Voice costs (per minute)

| Component | Cost per minute |
|-----------|-----------------|
| SIP/telephony (incoming) | 1–3 ₽ |
| STT (Yandex SpeechKit / Whisper API) | 2–8 ₽ |
| LLM processing | 1–5 ₽ |
| TTS (Yandex / ElevenLabs) | 3–10 ₽ |
| **Total voice per minute** | **7–25 ₽** |

### 5. Integration costs

| Integration | Cost |
|-------------|------|
| Telegram Bot API | Free |
| YooKassa | Commission 2.8–3.5% on payments (customer pays) |
| iiko API | Free with iiko subscription |
| SMS notifications | 2–5 ₽ per SMS |

### 6. Human costs (if hiring)

| Role | Monthly cost (Moscow/remote) |
|------|------------------------------|
| Junior backend developer | 100 000–180 000 ₽ |
| Middle fullstack | 200 000–350 000 ₽ |
| Senior engineer | 300 000–500 000 ₽ |
| Designer (part-time) | 50 000–150 000 ₽ |
| Customer success manager | 80 000–150 000 ₽ |
| Sales (part-time) | 50 000–100 000 ₽ + commission |
| Lawyer (consulting) | 10 000–50 000 ₽/month |
| Accountant (outsourced) | 5 000–15 000 ₽/month |

### 7. Marketing costs (early)

| Channel | Monthly budget |
|---------|---------------|
| Content creation | 0 (founder + AI) |
| Domain + hosting | 2 000 ₽ |
| Yandex Direct (later) | 30 000–100 000 ₽ |
| Design/video | 10 000–30 000 ₽ |
| **Early marketing total** | **5 000–20 000 ₽/month** |

---

## Revenue model

### Per-tenant revenue (Starter plan example: 35 000 ₽/month)

| Revenue item | Amount |
|-------------|--------|
| Monthly subscription | 35 000 ₽ |
| Setup fee (one-time, amortized over 6 months) | ~15 000 ₽/month |
| Usage overage (average) | 5 000 ₽ |
| **Effective monthly revenue per tenant** | **~55 000 ₽** |

### Cost per tenant (at 10-tenant scale)

| Cost item | Amount |
|-----------|--------|
| Infra share (30 000 ₽ / 10) | 3 000 ₽ |
| LLM costs (2000 conversations × 5 ₽) | 10 000 ₽ |
| Customer success time (2 hours × 1 500 ₽/hr) | 3 000 ₽ |
| Support/maintenance share | 2 000 ₽ |
| **Total cost per tenant** | **~18 000 ₽** |

### Gross margin per tenant

```
Revenue: 55 000 ₽
Cost: 18 000 ₽
Gross profit: 37 000 ₽
Gross margin: ~67%
```

---

## Breakeven analysis

### Solo founder scenario (no salary, minimal costs)

Fixed monthly costs:

| Item | Cost |
|------|------|
| Infrastructure | 25 000 ₽ |
| Tools/services | 5 000 ₽ |
| Marketing | 10 000 ₽ |
| Legal/accounting | 10 000 ₽ |
| **Total fixed** | **50 000 ₽** |

Breakeven: **2 paying tenants on Starter plan** (2 × 35 000 ₽ = 70 000 ₽ > 50 000 ₽ fixed + variable).

### With one employee scenario

Fixed monthly costs:

| Item | Cost |
|------|------|
| Infrastructure | 30 000 ₽ |
| Employee (customer success / junior dev) | 120 000 ₽ |
| Tools/services | 10 000 ₽ |
| Marketing | 20 000 ₽ |
| Legal/accounting | 15 000 ₽ |
| **Total fixed** | **195 000 ₽** |

Breakeven: **5–6 paying tenants**.

---

## Financial projections (12-month scenario)

### Conservative scenario

| Month | Tenants | MRR | Costs | Net |
|-------|---------|-----|-------|-----|
| 1–2 | 0 (building) | 0 | 50 000 ₽ | -100 000 ₽ |
| 3 | 1 pilot | 50 000 ₽ | 55 000 ₽ | -5 000 ₽ |
| 4 | 2 | 90 000 ₽ | 60 000 ₽ | +30 000 ₽ |
| 5 | 3 | 130 000 ₽ | 65 000 ₽ | +65 000 ₽ |
| 6 | 4 | 170 000 ₽ | 75 000 ₽ | +95 000 ₽ |
| 7–8 | 5–6 | 200–250 000 ₽ | 100 000 ₽ | +100–150 000 ₽ |
| 9–12 | 7–10 | 300–450 000 ₽ | 150 000 ₽ | +150–300 000 ₽ |

**Year 1 cumulative revenue (conservative):** 1.5–2.5M ₽.
**Year 1 net profit (solo founder):** 500 000–1 500 000 ₽.

### Optimistic scenario (with partnerships + Pro plans)

| Month | Tenants | MRR |
|-------|---------|-----|
| 6 | 8 | 400 000 ₽ |
| 9 | 15 | 750 000 ₽ |
| 12 | 25 | 1 500 000 ₽ |

**Year 1 ARR (optimistic):** 18M ₽.

---

## Investment requirements by phase

### Phase 1: First paid pilot (0–3 months)

| Item | Total |
|------|-------|
| Infrastructure | 75 000 ₽ |
| Tools and APIs | 15 000 ₽ |
| Legal setup | 30 000 ₽ |
| Marketing materials | 20 000 ₽ |
| **Total Phase 1** | **~140 000 ₽** |

### Phase 2: First 5 customers (3–6 months)

| Item | Total |
|------|-------|
| Infrastructure scale | 120 000 ₽ |
| LLM API costs | 100 000 ₽ |
| Marketing | 60 000 ₽ |
| Legal/compliance | 50 000 ₽ |
| Part-time help | 100 000 ₽ |
| **Total Phase 2** | **~430 000 ₽** |

### Phase 3: Growth (6–12 months)

| Item | Total |
|------|-------|
| Infrastructure | 300 000 ₽ |
| Team (1–2 people) | 1 000 000 ₽ |
| Marketing | 300 000 ₽ |
| Voice integration | 100 000 ₽ |
| **Total Phase 3** | **~1 700 000 ₽** |

### Total year 1 investment needed

- **Minimum (solo, bootstrapped):** 300 000–500 000 ₽.
- **Comfortable (with some help):** 1 000 000–2 000 000 ₽.
- **Aggressive (team + marketing):** 3 000 000–5 000 000 ₽.

---

## Key metrics to track

| Metric | Target |
|--------|--------|
| CAC (customer acquisition cost) | < 50 000 ₽ |
| LTV (lifetime value, 12 months) | > 400 000 ₽ |
| LTV:CAC ratio | > 5:1 |
| Payback period | < 2 months |
| Gross margin | > 65% |
| Monthly churn | < 5% |
| NRR (net revenue retention) | > 110% |
| Cost per AI conversation | < 10 ₽ |
| Cost per voice minute | < 25 ₽ |

---

## Pricing strategy evolution

| Stage | Strategy |
|-------|----------|
| First 3 pilots | Discounted/free setup, prove value | |
| 5–10 customers | Standard pricing, collect data | |
| 10–20 customers | Optimize based on usage patterns | |
| 20+ customers | Tiered pricing, vertical packages | |
| Enterprise | Custom pricing, SLA-based | |

---

## Risk to economics

| Risk | Mitigation |
|------|-----------|
| LLM costs spike | Caching, cheaper models for simple queries, usage caps |
| Low automation rate → high cost per resolution | Better knowledge, evaluation, preset tuning |
| Customer negotiates price too low | Published pricing, value-based selling, minimum commit |
| High churn | Success process, weekly reviews, ROI reports |
| Voice unprofitable | Separate voice pricing, optimize STT/TTS, batch processing |

---

## Summary

The business can become profitable with **2–3 paying customers** on minimal infrastructure. The key is to start cheap (API LLM, basic infra, no employees), prove value with pilots, then invest profits into growth. Do not hire or spend on marketing before product-market fit is confirmed by 3–5 paying customers.
