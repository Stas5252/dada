from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, field_serializer

from app.rbac import Role
from app.tool_registry import DEFAULT_ENABLED_TOOLS, normalize_enabled_tools


class TenantStatus(StrEnum):
    active = "active"
    suspended = "suspended"


class AgentStatus(StrEnum):
    draft = "draft"
    published = "published"
    archived = "archived"


class KnowledgeSourceStatus(StrEnum):
    pending = "pending"
    indexed = "indexed"
    failed = "failed"


class KnowledgeIngestionJobStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class ConversationStatus(StrEnum):
    open = "open"
    resolved = "resolved"
    escalated = "escalated"


class CrmLeadStatus(StrEnum):
    new = "new"
    qualified = "qualified"
    converted = "converted"
    lost = "lost"


class CrmDealStatus(StrEnum):
    open = "open"
    won = "won"
    lost = "lost"


class CrmTaskStatus(StrEnum):
    open = "open"
    done = "done"
    canceled = "canceled"


class MessageRole(StrEnum):
    customer = "customer"
    agent = "agent"
    operator = "operator"
    system = "system"


class ChannelAutomationMode(StrEnum):
    autopilot = "autopilot"
    draft_only = "draft_only"
    human_approval = "human_approval"


class ChannelCompliancePolicySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: ChannelAutomationMode = ChannelAutomationMode.autopilot
    outbound_enabled: bool = True
    ai_disclosure_required: bool = False
    require_opt_out_notice: bool = False
    require_contact_consent_for_outbound: bool = False
    max_auto_replies_per_conversation: int = Field(default=100, ge=0, le=1000)


class ChannelPoliciesSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_policy: ChannelCompliancePolicySettings = Field(
        default_factory=ChannelCompliancePolicySettings,
    )
    web_widget: ChannelCompliancePolicySettings = Field(
        default_factory=ChannelCompliancePolicySettings,
    )
    telegram: ChannelCompliancePolicySettings = Field(
        default_factory=ChannelCompliancePolicySettings,
    )
    vk: ChannelCompliancePolicySettings = Field(default_factory=ChannelCompliancePolicySettings)
    whatsapp: ChannelCompliancePolicySettings = Field(
        default_factory=ChannelCompliancePolicySettings,
    )
    voice: ChannelCompliancePolicySettings = Field(
        default_factory=ChannelCompliancePolicySettings,
    )


class IntegrationReadinessStatus(StrEnum):
    configured = "configured"
    local_stub = "local_stub"
    needs_setup = "needs_setup"


class IntegrationReadinessOverallStatus(StrEnum):
    ready = "ready"
    mock_mode = "mock_mode"
    action_required = "action_required"


class IntegrationReadinessItem(BaseModel):
    key: str
    label: str
    category: str
    status: IntegrationReadinessStatus
    summary: str
    required_settings: list[str] = Field(default_factory=list)
    configured_settings: list[str] = Field(default_factory=list)
    missing_settings: list[str] = Field(default_factory=list)
    setup_url: str | None = None
    docs_url: str | None = None
    blocking: bool = False


class IntegrationReadinessResponse(BaseModel):
    status: IntegrationReadinessOverallStatus
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    items: list[IntegrationReadinessItem]


class ChannelWebhookDiagnosticStatus(StrEnum):
    ready = "ready"
    warning = "warning"
    needs_setup = "needs_setup"


class ChannelWebhookPublicUrlStatus(StrEnum):
    https_ready = "https_ready"
    local_only = "local_only"
    missing = "missing"


class ChannelWebhookDiagnosticItem(BaseModel):
    key: str
    label: str
    provider: str
    status: ChannelWebhookDiagnosticStatus
    summary: str
    inbound_webhook_url: str | None = None
    required_settings: list[str] = Field(default_factory=list)
    configured_settings: list[str] = Field(default_factory=list)
    missing_settings: list[str] = Field(default_factory=list)
    setup_steps: list[str] = Field(default_factory=list)
    security_notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    setup_url: str | None = None
    docs_url: str | None = None
    test_mode: bool = True


class ChannelWebhookDiagnosticsResponse(BaseModel):
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    public_base_url: str
    public_url_status: ChannelWebhookPublicUrlStatus
    items: list[ChannelWebhookDiagnosticItem]


def _coerce_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items: Sequence[object] = value.replace(",", "\n").splitlines()
    elif isinstance(value, list):
        raw_items = value
    else:
        raise ValueError("Value must be a list of strings.")

    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        if not isinstance(item, str):
            raise ValueError("Every item must be a string.")
        normalized_item = " ".join(item.split())
        if not normalized_item or normalized_item in seen:
            continue
        normalized.append(normalized_item)
        seen.add(normalized_item)
    return normalized


class GuardrailPolicySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    opt_out_enabled: bool = True
    human_handoff_enabled: bool = True
    regulated_topics_enabled: bool = True
    prompt_injection_block_enabled: bool = True
    toxicity_escalation_enabled: bool = True
    outbound_safety_enabled: bool = True
    tool_safety_enabled: bool = True
    ai_disclosure_required: bool = False
    custom_regulated_terms: list[str] = Field(default_factory=list, max_length=50)
    custom_prohibited_claims: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("custom_regulated_terms", "custom_prohibited_claims", mode="before")
    @classmethod
    def normalize_phrase_list(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            raw_items: Sequence[object] = value.splitlines()
        elif isinstance(value, list):
            raw_items = value
        else:
            raise ValueError("Value must be a list of phrases.")

        normalized: list[str] = []
        seen: set[str] = set()
        for item in raw_items:
            if not isinstance(item, str):
                raise ValueError("Every phrase must be a string.")
            phrase = " ".join(item.split())
            if not phrase:
                continue
            if len(phrase) > 80:
                raise ValueError("Every phrase must be 80 characters or fewer.")
            phrase_key = phrase.casefold()
            if phrase_key in seen:
                continue
            seen.add(phrase_key)
            normalized.append(phrase)
        if len(normalized) > 50:
            raise ValueError("No more than 50 phrases are allowed.")
        return normalized


class TimestampedModel(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Tenant(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    plan: str = "start"
    status: TenantStatus = TenantStatus.active
    settings: dict[str, object] = Field(default_factory=dict)

    @field_serializer("settings")
    def mask_settings_secrets(self, settings: dict[str, object]) -> dict[str, object]:
        if not settings:
            return settings
        masked = dict(settings)
        for key in ["vk_group_token", "vk_confirmation_code"]:
            if masked.get(key):
                masked[key] = "***"
        return masked


class User(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    email: EmailStr
    name: str
    role: Role = Role.owner
    email_verified: bool = False
    totp_secret: str | None = None
    mfa_recovery_code_hashes: list[str] = Field(default_factory=list)


class UserPublic(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    email: EmailStr
    name: str
    role: Role = Role.owner
    email_verified: bool = False
    mfa_enabled: bool = False
    mfa_recovery_codes_remaining: int = 0


class AuthSession(TimestampedModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    refresh_token_hash: str
    expires_at: datetime
    revoked_at: datetime | None = None
    replaced_by_session_id: UUID | None = None


class AuditLog(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID | None = None
    user_id: UUID | None = None
    event_type: str
    ip_address: str | None = None
    details: dict[str, str] = Field(default_factory=dict)


class Agent(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    name: str
    prompt: str
    status: AgentStatus = AgentStatus.draft
    channel: str = "telegram"
    version: int = 1
    voice_id: str = "alloy"
    voice_language: str = "ru"
    voice_speed: float = 1.0
    temperature: float = 0.3
    max_tokens: int = 1024
    model_name: str = "gpt-4o-mini"
    reranker_threshold: float = 0.0
    telegram_bot_token: str | None = None
    pathway_nodes: list[dict[str, object]] | None = None
    pathway_edges: list[dict[str, object]] | None = None

    @field_serializer("telegram_bot_token")
    def mask_telegram_token(self, token: str | None) -> str | None:
        if not token:
            return token
        return "***"
    business_profile: str = ""
    agent_role: str = "customer_support"
    agent_tone: str = "professional"
    agent_language: str = "ru"
    business_hours: str = ""
    escalation_rules: str = ""
    sales_rules: str = ""
    forbidden_topics: list[str] = Field(default_factory=list)
    enabled_tools: list[str] = Field(default_factory=lambda: list(DEFAULT_ENABLED_TOOLS))


class KnowledgeSource(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    title: str
    source_type: str
    content: str
    status: KnowledgeSourceStatus = KnowledgeSourceStatus.indexed
    chunk_count: int = 1


class KnowledgeChunk(TimestampedModel):
    id: str
    tenant_id: UUID
    source_id: UUID
    chunk_index: int
    content: str
    content_hash: str
    embedding: list[float]
    qdrant_payload: dict[str, str] = Field(default_factory=dict)


class KnowledgeIngestionJob(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    source_id: UUID
    status: KnowledgeIngestionJobStatus = KnowledgeIngestionJobStatus.queued
    idempotency_key: str
    qdrant_collection: str
    background_backend: str = "inline-local"
    chunk_count: int = 0
    error_message: str | None = None


class QdrantCollectionContract(BaseModel):
    collection_name: str
    vector_size: int
    distance: str = "Cosine"
    vector_name: str = "content"
    payload_indexes: dict[str, str] = Field(default_factory=dict)

class RagEvalStatus(StrEnum):
    passed = "passed"
    failed = "failed"

class RagEvalCaseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    query: str = Field(min_length=2, max_length=1000)
    expected_source_titles: list[str] = Field(default_factory=list, max_length=10)
    expected_answer_terms: list[str] = Field(default_factory=list, max_length=20)
    should_answer: bool = True

class RagEvalRequest(BaseModel):
    cases: list[RagEvalCaseCreate] = Field(min_length=1, max_length=50)
    required_pass_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    min_relevance_score: float = Field(default=0.2, ge=0.0, le=1.0)

class RagEvalCaseResult(BaseModel):
    name: str
    status: RagEvalStatus
    query: str
    should_answer: bool
    retrieved_source_titles: list[str]
    citation_titles: list[str]
    matched_expected_terms: list[str]
    missing_expected_terms: list[str]
    no_answer_respected: bool
    relevance_score: float
    answer_preview: str
    failures: list[str]

class RagEvalResponse(BaseModel):
    status: RagEvalStatus
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    required_pass_rate: float
    min_relevance_score: float
    results: list[RagEvalCaseResult]


class QAEvaluation(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    conversation_id: UUID
    score: int = Field(ge=0, le=10)
    flags: list[str] = Field(default_factory=list)
    feedback: str = ""


class QAEvaluationRequest(BaseModel):
    conversation_id: UUID
    score: int = Field(ge=0, le=10)
    flags: list[str] = Field(default_factory=list)
    feedback: str = ""


class WeeklyReport(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    start_date: datetime
    end_date: datetime
    summary: str
    insights: str
    top_channels: list[str] = Field(default_factory=list)


class MarginDashboardResponse(BaseModel):
    total_revenue_minor: int
    total_costs_minor: int
    margin_minor: int
    currency: str = "RUB"
    margin_percentage: float


class Message(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    confidence: float | None = None
    source_ids: list[UUID] = Field(default_factory=list)


class Customer(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    external_id: str
    channel: str
    name: str | None = None
    phone: str | None = None
    tags: list[str] = Field(default_factory=list)


class ContactSuppression(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    channel: str
    contact_type: str
    value: str
    reason: str = "opt_out_requested"
    source: str = "runtime_guardrail"
    status: str = "active"


class ContactSuppressionCreateRequest(BaseModel):
    channel: str = Field(min_length=1, max_length=40)
    contact_type: str = Field(pattern=r"^(external_id|phone)$")
    value: str = Field(min_length=1, max_length=160)
    reason: str = Field(default="manual", min_length=1, max_length=120)
    source: str = Field(default="manual", min_length=1, max_length=80)


class ContactConsent(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    channel: str
    contact_type: str
    value: str
    consent_type: str = "outbound_contact"
    source: str = "manual"
    status: str = "active"
    expires_at: datetime | None = None


class ContactConsentCreateRequest(BaseModel):
    channel: str = Field(min_length=1, max_length=40)
    contact_type: str = Field(pattern=r"^(external_id|phone)$")
    value: str = Field(min_length=1, max_length=160)
    consent_type: str = Field(default="outbound_contact", min_length=1, max_length=80)
    source: str = Field(default="manual", min_length=1, max_length=80)
    expires_at: datetime | None = None


class CustomerCreate(BaseModel):
    external_id: str
    channel: str
    name: str | None = None
    phone: str | None = None
    tags: list[str] = Field(default_factory=list)


class CustomerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    tags: list[str] | None = None


class CrmSource(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    name: str
    channel: str = "manual"
    external_id: str | None = None


class CrmSourceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    channel: str = Field(default="manual", min_length=1, max_length=40)
    external_id: str | None = Field(default=None, max_length=160)


class CrmCompany(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    name: str
    website: str | None = None
    phone: str | None = None
    custom_fields: dict[str, str] = Field(default_factory=dict)


class CrmCompanyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    website: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    custom_fields: dict[str, str] = Field(default_factory=dict)


class CrmPipeline(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    name: str
    is_default: bool = False


class CrmPipelineCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    is_default: bool = False


class CrmStage(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    pipeline_id: UUID
    name: str
    position: int = 0
    probability: int = 0


class CrmStageCreateRequest(BaseModel):
    pipeline_id: UUID
    name: str = Field(min_length=1, max_length=120)
    position: int = Field(default=0, ge=0, le=1000)
    probability: int = Field(default=0, ge=0, le=100)


class CrmLead(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    company_id: UUID | None = None
    customer_id: UUID | None = None
    conversation_id: UUID | None = None
    name: str
    phone: str | None = None
    email: str | None = None
    source: str = "manual"
    status: CrmLeadStatus = CrmLeadStatus.new
    score: int = 0
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, str] = Field(default_factory=dict)


class CrmLeadCreateRequest(BaseModel):
    company_id: UUID | None = None
    customer_id: UUID | None = None
    conversation_id: UUID | None = None
    name: str = Field(min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    source: str = Field(default="manual", min_length=1, max_length=120)
    status: CrmLeadStatus = CrmLeadStatus.new
    score: int = Field(default=0, ge=0, le=100)
    tags: list[str] = Field(default_factory=list, max_length=50)
    custom_fields: dict[str, str] = Field(default_factory=dict)

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value: object) -> list[str]:
        return _coerce_string_list(value)


class CrmDeal(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    lead_id: UUID | None = None
    company_id: UUID | None = None
    pipeline_id: UUID | None = None
    stage_id: UUID | None = None
    title: str
    amount_minor: int = 0
    currency: str = "RUB"
    status: CrmDealStatus = CrmDealStatus.open
    source: str = "manual"
    custom_fields: dict[str, str] = Field(default_factory=dict)
    expected_close_at: datetime | None = None


class CrmDealCreateRequest(BaseModel):
    lead_id: UUID | None = None
    company_id: UUID | None = None
    pipeline_id: UUID | None = None
    stage_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    amount_minor: int = Field(default=0, ge=0)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    status: CrmDealStatus = CrmDealStatus.open
    source: str = Field(default="manual", min_length=1, max_length=120)
    custom_fields: dict[str, str] = Field(default_factory=dict)
    expected_close_at: datetime | None = None
    lead_name: str | None = Field(default=None, max_length=160)
    lead_phone: str | None = Field(default=None, max_length=40)
    lead_email: EmailStr | None = None


class CrmTask(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    lead_id: UUID | None = None
    deal_id: UUID | None = None
    title: str
    status: CrmTaskStatus = CrmTaskStatus.open
    due_at: datetime | None = None
    assignee_user_id: UUID | None = None


class CrmTaskCreateRequest(BaseModel):
    lead_id: UUID | None = None
    deal_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    status: CrmTaskStatus = CrmTaskStatus.open
    due_at: datetime | None = None
    assignee_user_id: UUID | None = None


class CrmNote(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    lead_id: UUID | None = None
    deal_id: UUID | None = None
    conversation_id: UUID | None = None
    body: str
    author_user_id: UUID | None = None


class CrmNoteCreateRequest(BaseModel):
    lead_id: UUID | None = None
    deal_id: UUID | None = None
    conversation_id: UUID | None = None
    body: str = Field(min_length=1, max_length=4000)
    author_user_id: UUID | None = None


class ConversationCreateRequest(BaseModel):
    customer_id: UUID | None = None
    initial_message: str | None = None


class OrderItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    product_name: str
    product_external_id: str | None = None
    quantity: int
    price_per_unit: int
    created_at: datetime


class OrderDraft(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    conversation_id: UUID
    customer_phone: str | None = None
    delivery_address: str | None = None
    status: str
    total_amount: int
    created_at: datetime
    updated_at: datetime
    items: list[OrderItem] = Field(default_factory=list)


class Conversation(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    agent_id: UUID
    customer_id: UUID | None = None
    channel: str
    status: ConversationStatus = ConversationStatus.open
    summary: str = ""
    resolution_status: str = "unresolved"
    priority: str = "normal"
    sla_due_at: datetime | None = None
    handoff_status: str = "ai_handling"
    assigned_user_id: UUID | None = None


class RegisterRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=120)
    owner_email: EmailStr
    owner_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_expires_at: datetime
    refresh_expires_at: datetime


class RegisterResponse(TokenPairResponse):
    tenant: Tenant
    user: UserPublic


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginResponse(TokenPairResponse):
    tenant: Tenant | None = None
    user: UserPublic | None = None
    requires_mfa: bool = False


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=512)


class RefreshTokenResponse(TokenPairResponse):
    pass


class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class MFARecoveryCodesResponse(BaseModel):
    codes: list[str]
    remaining: int


class MFAVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)
    secret: str


class MFACodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=32)


class LoginMFARequest(BaseModel):
    token: str = Field(min_length=1)  # Intermediate token from login
    code: str = Field(min_length=6, max_length=32)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=512)


class EmailVerificationRequest(BaseModel):
    token: str = Field(min_length=1)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class VerificationToken(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    token_hash: str
    expires_at: datetime
    used_at: datetime | None = None


class PasswordResetToken(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    token_hash: str
    expires_at: datetime
    used_at: datetime | None = None


class AgentCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    prompt: str = Field(min_length=10, max_length=4000)
    channel: str = "telegram"
    voice_id: str = "alloy"
    voice_language: str = "ru"
    voice_speed: float = 1.0
    temperature: float = 0.3
    max_tokens: int = 1024
    model_name: str = "gpt-4o-mini"
    reranker_threshold: float = 0.0
    pathway_nodes: list[dict[str, object]] | None = None
    pathway_edges: list[dict[str, object]] | None = None
    business_profile: str = Field(default="", max_length=4000)
    agent_role: str = Field(default="customer_support", min_length=1, max_length=120)
    agent_tone: str = Field(default="professional", min_length=1, max_length=120)
    agent_language: str = Field(default="ru", min_length=1, max_length=40)
    business_hours: str = Field(default="", max_length=1000)
    escalation_rules: str = Field(default="", max_length=2000)
    sales_rules: str = Field(default="", max_length=2000)
    forbidden_topics: list[str] = Field(default_factory=list, max_length=50)
    enabled_tools: list[str] = Field(default_factory=lambda: list(DEFAULT_ENABLED_TOOLS), max_length=30)

    @field_validator("forbidden_topics", mode="before")
    @classmethod
    def _normalize_forbidden_topics(cls, value: object) -> list[str]:
        return _coerce_string_list(value)

    @field_validator("enabled_tools", mode="before")
    @classmethod
    def _normalize_enabled_tools(cls, value: object) -> list[str]:
        return normalize_enabled_tools(_coerce_string_list(value))


class AgentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    prompt: str | None = Field(default=None, min_length=10, max_length=4000)
    channel: str | None = None
    voice_id: str | None = None
    voice_language: str | None = None
    voice_speed: float | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    model_name: str | None = None
    reranker_threshold: float | None = None
    telegram_bot_token: str | None = None
    pathway_nodes: list[dict[str, object]] | None = None
    pathway_edges: list[dict[str, object]] | None = None
    business_profile: str | None = Field(default=None, max_length=4000)
    agent_role: str | None = Field(default=None, min_length=1, max_length=120)
    agent_tone: str | None = Field(default=None, min_length=1, max_length=120)
    agent_language: str | None = Field(default=None, min_length=1, max_length=40)
    business_hours: str | None = Field(default=None, max_length=1000)
    escalation_rules: str | None = Field(default=None, max_length=2000)
    sales_rules: str | None = Field(default=None, max_length=2000)
    forbidden_topics: list[str] | None = Field(default=None, max_length=50)
    enabled_tools: list[str] | None = Field(default=None, max_length=30)

    @field_validator("forbidden_topics", mode="before")
    @classmethod
    def _normalize_forbidden_topics(cls, value: object) -> list[str] | None:
        return None if value is None else _coerce_string_list(value)

    @field_validator("enabled_tools", mode="before")
    @classmethod
    def _normalize_enabled_tools(cls, value: object) -> list[str] | None:
        return None if value is None else normalize_enabled_tools(_coerce_string_list(value))


class KnowledgeSourceCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    source_type: str = "manual"
    content: str = Field(min_length=2, max_length=20000)


class TelegramConnectRequest(BaseModel):
    bot_token: str = Field(min_length=10, description="Telegram bot token")


class ChatMessageRequest(BaseModel):
    agent_id: UUID
    conversation_id: UUID | None = None
    channel: str = "web_widget"
    message: str = Field(min_length=1, max_length=4000)


class ChatMessageResponse(BaseModel):
    conversation: Conversation
    customer_message: Message
    agent_message: Message
    sources: list[KnowledgeSource]


class ConversationDetail(BaseModel):
    conversation: Conversation
    messages: list[Message]
    sources: list[KnowledgeSource]


class DashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant: Tenant
    agents_total: int
    knowledge_sources_total: int
    conversations_total: int
    automation_rate: float
    unresolved_topics_total: int


class ApiKey(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    name: str
    key_prefix: str
    key_hash: str
    created_by: UUID
    scopes: list[str] = Field(default_factory=lambda: ["read"])
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None

class TestCaseStatus(StrEnum):
    running = "running"
    passed = "passed"
    failed = "failed"

class TestCaseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    scenario: str = Field(min_length=10, max_length=2000)
    expected_outcome: str = Field(min_length=2, max_length=1000)

class TestCase(TestCaseCreate, TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    agent_id: UUID

class TestRunBase(BaseModel):
    status: TestCaseStatus = TestCaseStatus.running
    logs: list[dict[str, object]] = Field(default_factory=list)
    result_summary: str | None = None

class TestRun(TestRunBase, TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    agent_id: UUID
    test_case_id: UUID

class TestbedReadinessStatus(StrEnum):
    ready = "ready"
    action_required = "action_required"

class TestbedCaseReadinessStatus(StrEnum):
    passed = "passed"
    failed = "failed"
    running = "running"
    stale_run = "stale_run"
    missing_run = "missing_run"

class TestbedLatestRunSummary(BaseModel):
    id: UUID
    status: TestCaseStatus
    result_summary: str | None = None
    created_at: datetime
    updated_at: datetime

class TestbedCaseReadiness(BaseModel):
    test_case_id: UUID
    test_case_name: str
    status: TestbedCaseReadinessStatus
    latest_run: TestbedLatestRunSummary | None = None
    required_action: str | None = None

class TestbedReadinessResponse(BaseModel):
    agent_id: UUID
    checked_at: datetime
    status: TestbedReadinessStatus
    publish_blocked: bool
    required_pass_rate: float
    minimum_test_cases: int
    total_cases: int
    passing_cases: int
    failing_cases: int
    running_cases: int
    stale_cases: int
    missing_run_cases: int
    pass_rate: float
    failures: list[dict[str, str]]
    cases: list[TestbedCaseReadiness]
