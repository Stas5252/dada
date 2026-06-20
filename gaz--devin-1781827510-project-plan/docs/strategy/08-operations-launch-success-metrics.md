# 08. Operations, launch and success metrics

## Environments

### Development

- local Docker Compose;
- mock/local adapters;
- seed/demo tenant;
- fast tests.

### Staging

- real HTTPS;
- PostgreSQL/Qdrant/Redis/Object Storage;
- provider sandboxes;
- separate secrets;
- staging smoke tests;
- test customer tenants.

### Production

- managed infrastructure in RF region for Russian personal data;
- backups;
- monitoring;
- incident response;
- deploy rollback;
- customer support process.

## Observability

Metrics:

- API latency p50/p95/p99;
- error rate;
- queue depth;
- ingestion job duration/failures;
- LLM latency/cost;
- RAG hit rate;
- no-answer rate;
- action success/failure;
- voice turn latency;
- provider webhook failures.

Logs:

- structured JSON;
- correlation ID;
- tenant ID;
- no raw secrets;
- PII masked where possible.

Traces:

- conversation orchestration;
- RAG retrieval;
- LLM call;
- action execution;
- external provider calls.

Alerts:

- API 5xx spike;
- queue stuck;
- provider failure;
- hallucination/eval regression;
- payment webhook failures;
- backup failure;
- DB storage/CPU.

## Customer success process

### Pre-launch checklist

- signed agreement;
- data processing docs;
- tenant created;
- channels connected;
- knowledge loaded;
- golden questions approved;
- operator handoff configured;
- billing enabled;
- launch date agreed.

### First week

- daily report;
- review unresolved topics;
- tune knowledge;
- fix failed actions;
- measure ROI;
- collect operator feedback.

### Monthly business review

- automation rate;
- saved hours;
- revenue/orders assisted;
- quality incidents;
- knowledge gaps;
- next integrations.

## Success metrics

### Product metrics

- time to first answer;
- time to first live channel;
- automation rate;
- no-answer accuracy;
- source attribution rate;
- operator handoff quality;
- feature adoption.

### Business metrics

- trial-to-paid conversion;
- CAC payback;
- MRR/ARR;
- churn;
- expansion revenue;
- gross margin;
- implementation cost per client.

### Customer ROI metrics

- saved operator hours;
- reduced first response time;
- reduced missed leads;
- increased orders/bookings;
- reduced support backlog;
- CSAT/NPS impact.

## Launch sequence

1. Internal staging demo.
2. Friendly pilot with one real business.
3. Fix reliability/security gaps.
4. Add 3–5 pilots in same vertical.
5. Publish first case study.
6. Build partner channel.
7. Scale to adjacent verticals.

## Support model

Support tiers:

- Basic: email/Telegram support, 1 business day.
- Pro: priority, monthly review.
- Enterprise: SLA, dedicated channel, custom integrations.

Incident severity:

- SEV1: production down/payment/security issue;
- SEV2: major channel/provider broken;
- SEV3: degraded AI quality;
- SEV4: minor UI/docs issue.
