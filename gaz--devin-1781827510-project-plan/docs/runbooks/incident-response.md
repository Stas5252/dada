# Incident Response and Recovery Runbook

This document details standard procedures for responding to common production incidents in the CallForce platform.

---

## 1. iiko API Outage or Connection Failures

### Symptoms
- API logs contain `IntegrationsException` or `HTTPException(status_code=502)` on orders flow.
- Operator console shows orders stuck in "failed" state.

### Diagnosis
Verify connectivity to iiko sandbox/production endpoint:
```powershell
# Check if API can reach iiko domain
curl -I https://api-ru.iiko.services
```

### Recovery & Fallback Procedure
1. **Auto-fallback to Operator**: The platform automatically transitions stuck orders to `escalated` and queues them in the **Operator Console**.
2. **Contact Operator Team**: Instruct operators to manually register orders in the iiko POS terminal.
3. **Verify Secrets**: Ensure `IIKO_API_LOGIN` and `IIKO_API_PASSWORD` are valid in `.env` config.

---

## 2. Qdrant / RAG Search and Ingestion Failures

### Symptoms
- "Ой, к сожалению, у меня нет под рукой этой информации..." answered for standard questions.
- Knowledge Source status shows `failed` in the client dashboard.

### Diagnosis
1. Verify Qdrant vector DB container status:
   ```powershell
   docker compose -f infra/docker-compose.local.yml ps qdrant
   ```
2. Verify vector collection exists:
   ```powershell
   curl http://localhost:6333/collections/callforce_knowledge_chunks
   ```

### Recovery Procedure
1. **Restart Qdrant Service**:
   ```powershell
   docker compose -f infra/docker-compose.local.yml restart qdrant
   ```
2. **Trigger Re-indexing**:
   - Run manual re-indexing script or click "Re-index" in the client settings UI.
   - Using curl command:
     ```powershell
     curl -X POST http://localhost:8000/api/v1/knowledge/reindex -H "Authorization: Bearer <token>"
     ```

---

## 3. High LLM Latency or Provider Timeout

### Symptoms
- Chat responses take > 5 seconds, or voice streaming encounters timeout logs.
- Metric `http_request_duration_seconds` shows p95 spike.

### Diagnosis
Check which provider is actively serving requests in `.env`:
- `LLM_PROVIDER` (options: `auto`, `openai`, `vllm`).

### Recovery Procedure
1. **Fallback Routing**: If `vllm` is experiencing high load/GPU issues, switch provider to `openai` by modifying the environment:
   ```env
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your-key-here
   ```
2. **Restart API Service**:
   ```powershell
   docker compose restart api
   ```

---

## 4. API Service Spikes (5xx Error Storm)

### Symptoms
- High HTTP 5xx rate alert triggers.
- Clients experience slow load times or socket connection drops.

### Diagnosis
Inspect uvicorn container logs for python exceptions:
```powershell
docker compose logs api --tail 100 -f
```

### Recovery Procedure
1. **Scale Containers**:
   ```powershell
   docker compose up -d --scale api=3
   ```
2. **Check Redis Connection**: If rate limiter fails, verify redis health:
   ```powershell
   docker compose exec redis redis-cli ping
   ```

---

## 5. YooKassa Payment Webhook Verification Failures

### Symptoms
- Client paid for a subscription, but billing limits did not update.
- Webhook endpoints log `Signature verification failed` or returns 400.

### Diagnosis
Check logs for `/webhooks/yookassa` endpoint. Verify that the IP address matches YooKassa's official subnets (`185.71.76.0/27`, `185.71.77.0/27`, etc.).

### Manual Credit Procedure
If payment succeeded but webhook failed:
1. Access PostgreSQL DB:
   ```powershell
   docker compose exec db psql -U callforce -d callforce
   ```
2. Manually credit the client's balance:
   ```sql
   UPDATE billing_accounts SET balance = balance + <paid_amount> WHERE tenant_id = '<tenant_uuid>';
   ```
