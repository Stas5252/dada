from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.rbac import Role


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


class MessageRole(StrEnum):
    customer = "customer"
    agent = "agent"
    operator = "operator"
    system = "system"


class TimestampedModel(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Tenant(TimestampedModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    plan: str = "start"
    status: TenantStatus = TenantStatus.active
    settings: dict[str, object] = Field(default_factory=dict)


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
    telegram_bot_token: str | None = None
    pathway_nodes: list[dict[str, object]] | None = None
    pathway_edges: list[dict[str, object]] | None = None


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
    pathway_nodes: list[dict[str, object]] | None = None
    pathway_edges: list[dict[str, object]] | None = None


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
    telegram_bot_token: str | None = None
    pathway_nodes: list[dict[str, object]] | None = None
    pathway_edges: list[dict[str, object]] | None = None


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
