# CallForce Execution Roadmap

This document breaks down the implementation of the CallForce master plan into small, manageable PRs/slices, executed in order.

## 1. Real Alembic migration baseline
- [x] Configure Alembic `alembic.ini` and `env.py` for FastAPI integration.
- [x] Connect `SqlAlchemyStore` metadata to Alembic.
- [x] Generate the initial baseline migration `0001_initial_baseline.py` replacing `.sql` files.
- [x] Update `make migrate` to use Alembic.
- [x] Acceptance: `make test` passes, DB is correctly migrated, rollback works.

## 2. Customer profile + channel identity
- [x] Create `customers` table with `tenant_id`, `external_id`, `channel` fields.
- [x] Link `conversations` and `messages` to `customer_id`.
- [x] Add API for creating/updating customer profile (name, phone, tags).
- [x] Acceptance: A conversation started via widget or Telegram correctly identifies or creates a customer profile.

## 3. Operator Inbox v1
- [x] Add `operator_queue` table or `status` field to `conversations`.
- [x] API for operators to list active/escalated conversations.
- [x] API to claim conversation, send messages, and close.
- [x] WebSocket/Polling for real-time updates in operator console.
- [x] Frontend: Basic Operator Console UI.
- [x] Acceptance: Agent can escalate a chat, operator sees it in inbox, replies, and client receives the message.

## 4. Widget production channel [x]
- [x] Stabilize web widget bundle and API.
- [x] Secure CORS and rate limiting for widget.
- [x] Collect customer info (name/phone optionally) before chat.
- [x] Acceptance: Widget can be embedded on any site, creates persistent sessions, connects to AI and Operator.

## 5. Telegram setup wizard [x]
- [x] UI for connecting Telegram bot token.
- [x] Encrypted storage of Telegram tokens.
- [x] Setup webhook dynamically via Telegram API.
- [x] Handle Telegram updates, route to Agent/Operator.
- [x] Acceptance: User inputs token, bot starts answering via CallForce.

## 6. Knowledge/eval lab [x]
- [x] Replace local embedding stub with Qdrant real integration.
- [x] Better PDF/DOCX parsing pipeline.
- [x] Test console evaluation metrics (confidence, citations).
- [x] Acceptance: Uploading a complex menu PDF yields accurate RAG answers with citations.

## 7. Order draft engine [x]
- [x] DB models for `order_drafts` and `order_items`.
- [x] Tool/action for Agent to add/remove items from cart.
- [x] Explicit order confirmation step.
- [x] Acceptance: AI can assemble a pizza order and ask for confirmation before sending to POS.

## 8. POS/iiko/r_keeper [x]
- [x] Implement iiko adapter (menus, stop-lists, order submission).
- [x] Sync iiko menu to Knowledge/RAG.
- [x] Submit confirmed order to iiko.
- [x] Acceptance: Confirmed order from chat appears in iiko POS.

## 9. Phone number/SIP/voice
- [ ] SIP trunk configuration UI.
- [ ] Asterisk/ARI integration for inbound voice.
- [ ] Streaming STT (Faster-Whisper) and TTS integration.
- [ ] Voice state machine execution.
- [ ] Acceptance: Calling a SIP number talks to the AI agent with < 1.5s latency.

## 10. WhatsApp/VK
- [ ] WhatsApp Business API integration setup.
- [ ] VK community messages webhook setup.
- [ ] Acceptance: Bots work identically in WA and VK.

## 11. Billing/security/ops hardening
- [ ] YooKassa subscription billing.
- [ ] Tenant limits enforcement (messages, voice minutes).
- [ ] Finalize logging, PII masking, metrics.
- [ ] E2E/Load tests and staging deployment.
- [ ] Acceptance: Platform ready for real public launch.
