import {
  fetchCoreApi,
  getCoreTenantId,
  type CoreAgent,
  type CoreConversation,
  type CoreConversationDetail,
  type CoreDashboardResponse,
  type CoreKnowledgeIngestionJob,
  type CoreKnowledgeSource,
  type CoreReadinessResponse,
} from "./core-api";

export type ApiState = "live" | "mock" | "empty" | "error";

export type ApiResult<T> = {
  data: T;
  state: ApiState;
  path: string;
  message?: string;
};

export type OnboardingItem = {
  id: string;
  title: string;
  description: string;
  status: "done" | "current" | "blocked" | "pending";
  href: string;
};

export type DashboardOverview = {
  kpis: Array<{
    label: string;
    value: string;
    detail: string;
  }>;
  alerts: Array<{
    title: string;
    tone: "ok" | "warn" | "danger";
    description: string;
  }>;
};

export type ProductionReadiness = {
  status: "ready" | "degraded";
  environment: string;
  storeBackend: string;
  providers: Array<{
    name: string;
    status: "configured" | "missing_secret" | "local_stub";
    detail: string;
  }>;
};

export type Agent = {
  channel: string;
  id: string;
  name: string;
  status: "draft" | "testing" | "published" | "archived";
  channels: string[];
  version: string;
  updatedAt: string;
  goal: string;
  voiceId: string;
  voiceLanguage: string;
  voiceSpeed: number;
  temperature: number;
  maxTokens: number;
  modelName: string;
};

export type KnowledgeSource = {
  id: string;
  name: string;
  type: "file" | "url" | "integration";
  syncStatus: "indexed" | "processing" | "needs_review" | "pending" | "failed";
  documents: number;
  coverageScore: number;
  updatedAt: string;
};

export type KnowledgeIngestionJob = {
  backend: string;
  chunkCount: number;
  collection: string;
  errorMessage?: string;
  id: string;
  sourceId: string;
  status: "queued" | "running" | "completed" | "failed";
  updatedAt: string;
};

export type ConversationSummary = {
  id: string;
  channel: "Telegram" | "SIP" | "Widget";
  customer: string;
  status: "open" | "resolved" | "escalated" | "draft";
  summary: string;
  latency: string;
  updatedAt: string;
};

export type ConversationMessage = {
  id: string;
  role: "customer" | "agent" | "operator" | "system";
  content: string;
  createdAt: string;
  sources?: string[];
};

export type ConversationDetail = ConversationSummary & {
  resolution: string;
  handoffReason?: string;
  messages: ConversationMessage[];
  tools: Array<{
    name: string;
    status: "success" | "skipped" | "failed";
    latency: string;
  }>;
};

export const onboardingItems: OnboardingItem[] = [
  {
    id: "tenant",
    title: "Создать tenant и профиль бизнеса",
    description: "Базовая регистрация, язык, отрасль, timezone и SLA ожидания.",
    status: "done",
    href: "/onboarding",
  },
  {
    id: "agent",
    title: "Собрать draft агента",
    description: "Prompt, policy, каналы, handoff rules и первая версия сценария.",
    status: "current",
    href: "/agents/new",
  },
  {
    id: "knowledge",
    title: "Загрузить knowledge source",
    description: "Меню, FAQ или URL для mock RAG ответа с attribution.",
    status: "pending",
    href: "/knowledge",
  },
  {
    id: "conversation",
    title: "Пройти тестовый диалог",
    description: "Проверить ответ, sources, latency, summary и conversation log.",
    status: "done",
    href: "/test-console",
  },
  {
    id: "publish",
    title: "Опубликовать MVP канал",
    description: "Публикация доступна из карточки агента и страницы редактирования.",
    status: "done",
    href: "/agents",
  },
  {
    id: "telegram",
    title: "Подключить Telegram бота",
    description: "Получите токен в @BotFather и укажите его в настройках канала Telegram.",
    status: "current",
    href: "/agents",
  },
  {
    id: "widget",
    title: "Установить Web Widget",
    description: "Скопируйте snippet <script src=\"...\"> на свой сайт для запуска чата.",
    status: "pending",
    href: "/dashboard",
  },
];

const dashboardOverview: DashboardOverview = {
  kpis: [
    { label: "Диалоги", value: "128", detail: "+18% за 7 дней" },
    { label: "Automation rate", value: "62%", detail: "MVP target: 60%" },
    { label: "p95 latency", value: "1.4с", detail: "Chat target: <2с" },
    { label: "Usage cost", value: "3 840₽", detail: "Start plan estimate" },
  ],
  alerts: [
    {
      title: "Knowledge coverage ниже цели",
      tone: "warn",
      description: "Добавьте меню и правила доставки, чтобы снизить unresolved topics.",
    },
    {
      title: "Telegram канал готов к sandbox тесту",
      tone: "ok",
      description: "Webhook endpoint запланирован как /api/v1/chat/webhook/telegram/{token}.",
    },
  ],
};

const productionReadiness: ProductionReadiness = {
  status: "degraded",
  environment: "local",
  storeBackend: "memory",
  providers: [
    {
      name: "telegram",
      status: "local_stub",
      detail: "Local stub active until TELEGRAM_BOT_TOKEN is configured.",
    },
    {
      name: "yookassa",
      status: "local_stub",
      detail: "Local stub active until YooKassa credentials are configured.",
    },
    {
      name: "iiko",
      status: "local_stub",
      detail: "Local stub active until iiko credentials are configured.",
    },
    {
      name: "asterisk_ari",
      status: "local_stub",
      detail: "Local stub active until SIP/ARI credentials are configured.",
    },
  ],
};

const agents: Agent[] = [
  {
    id: "agent-restaurant-support",
    channel: "telegram",
    name: "Restaurant Support RU",
    status: "testing",
    channels: ["Telegram", "Widget"],
    version: "v0.3 draft",
    updatedAt: "2026-06-18",
    goal: "FAQ, доставка, статус заказа и handoff оператору.",
    voiceId: "alloy",
    voiceLanguage: "ru",
    voiceSpeed: 1.0,
    temperature: 0.3,
    maxTokens: 1024,
    modelName: "gpt-4o-mini",
  },
  {
    id: "agent-voice-frontdesk",
    channel: "sip",
    name: "Voice Frontdesk",
    status: "draft",
    channels: ["SIP"],
    version: "v0.1 draft",
    updatedAt: "2026-06-17",
    goal: "Принимать звонки, уточнять заказ и переводить сложные кейсы.",
    voiceId: "alloy",
    voiceLanguage: "ru",
    voiceSpeed: 1.0,
    temperature: 0.3,
    maxTokens: 1024,
    modelName: "gpt-4o-mini",
  },
];

const knowledgeSources: KnowledgeSource[] = [
  {
    id: "ks-menu-faq",
    name: "Меню и FAQ доставки.pdf",
    type: "file",
    syncStatus: "indexed",
    documents: 18,
    coverageScore: 78,
    updatedAt: "2026-06-18 19:10",
  },
  {
    id: "ks-website",
    name: "https://demo-restaurant.example/faq",
    type: "url",
    syncStatus: "processing",
    documents: 6,
    coverageScore: 52,
    updatedAt: "2026-06-18 20:05",
  },
  {
    id: "ks-iiko",
    name: "iiko menu sync",
    type: "integration",
    syncStatus: "needs_review",
    documents: 0,
    coverageScore: 0,
    updatedAt: "Не подключено",
  },
];

const ingestionJobs: KnowledgeIngestionJob[] = [
  {
    backend: "inline-local",
    chunkCount: 1,
    collection: "callforce_knowledge",
    id: "job-demo-delivery-faq",
    sourceId: "ks-menu-faq",
    status: "completed",
    updatedAt: "2026-06-18 19:10",
  },
];

const conversations: ConversationDetail[] = [
  {
    id: "conv-1001",
    channel: "Telegram",
    customer: "Анна П.",
    status: "resolved",
    summary: "Клиент уточнил время доставки и получил ссылку на оплату.",
    latency: "0.8с",
    updatedAt: "12 минут назад",
    resolution: "Ответ закрыт автоматически с источником из FAQ доставки.",
    messages: [
      {
        id: "msg-1",
        role: "customer",
        content: "Здравствуйте, сколько обычно занимает доставка на Невский?",
        createdAt: "18:42",
      },
      {
        id: "msg-2",
        role: "agent",
        content: "Обычно 45–60 минут. Сейчас зона Невского доступна, могу помочь оформить заказ.",
        createdAt: "18:42",
        sources: ["Меню и FAQ доставки.pdf", "Delivery SLA policy"],
      },
      {
        id: "msg-3",
        role: "customer",
        content: "Да, пришлите оплату для пепперони 30 см.",
        createdAt: "18:43",
      },
      {
        id: "msg-4",
        role: "agent",
        content: "Сформировал черновик заказа. Перед оплатой подтвердите: пепперони 30 см, доставка на Невский.",
        createdAt: "18:43",
      },
    ],
    tools: [
      { name: "order.create_draft", status: "success", latency: "320мс" },
      { name: "payment.link", status: "skipped", latency: "requires confirmation" },
    ],
  },
  {
    id: "conv-1002",
    channel: "SIP",
    customer: "Номер +7 *** 21-45",
    status: "escalated",
    summary: "Клиент просил изменить состав заказа после передачи на кухню.",
    latency: "1.4с",
    updatedAt: "28 минут назад",
    resolution: "Передано оператору из-за правила изменения заказа после подтверждения.",
    handoffReason: "Order already in progress",
    messages: [
      {
        id: "msg-5",
        role: "customer",
        content: "Можно убрать грибы из заказа, который я уже оплатил?",
        createdAt: "18:18",
      },
      {
        id: "msg-6",
        role: "agent",
        content: "Проверяю статус заказа. Если кухня еще не начала готовить, изменение возможно.",
        createdAt: "18:18",
      },
      {
        id: "msg-7",
        role: "system",
        content: "Заказ уже передан на кухню. Требуется оператор.",
        createdAt: "18:19",
      },
      {
        id: "msg-8",
        role: "operator",
        content: "Я подключаюсь и уточню возможность изменения у кухни.",
        createdAt: "18:19",
      },
    ],
    tools: [{ name: "order.status", status: "success", latency: "410мс" }],
  },
  {
    id: "conv-1003",
    channel: "Widget",
    customer: "Гость сайта",
    status: "draft",
    summary: "Вопрос о сертификатах не найден в базе знаний.",
    latency: "1.1с",
    updatedAt: "1 час назад",
    resolution: "Помечено как unresolved topic для RAG coverage.",
    handoffReason: "No answer policy",
    messages: [
      {
        id: "msg-9",
        role: "customer",
        content: "Есть подарочные сертификаты на мастер-класс?",
        createdAt: "17:35",
      },
      {
        id: "msg-10",
        role: "agent",
        content: "Я не нашел подтвержденной информации в базе знаний и передам вопрос оператору.",
        createdAt: "17:35",
      },
    ],
    tools: [{ name: "rag.search", status: "failed", latency: "120мс" }],
  },
];

function hasEmptyPayload<T>(payload: T | null): boolean {
  if (Array.isArray(payload)) {
    return payload.length === 0;
  }

  if (payload === null) {
    return true;
  }

  if (typeof payload === "object") {
    return Object.keys(payload as Record<string, unknown>).length === 0;
  }

  return false;
}

function resultFromFallback<T>(
  path: string,
  fallback: T,
  state: Exclude<ApiState, "live">,
  message?: string,
): ApiResult<T> {
  return {
    data: fallback,
    state: hasEmptyPayload(fallback) ? "empty" : state,
    path,
    message,
  };
}

async function fetchMappedCoreData<TCore, TData>(
  path: string,
  fallback: TData,
  mapData: (payload: TCore) => TData,
): Promise<ApiResult<TData>> {
  const result = await fetchCoreApi<TCore>(path);

  if (result.state !== "live") {
    return resultFromFallback(path, fallback, result.state, result.message);
  }

  const data = mapData(result.data);

  return {
    data,
    state: hasEmptyPayload(data) ? "empty" : "live",
    path,
  };
}

function formatDateTime(value: string) {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(parsed);
}

function formatChannel(channel: string): ConversationSummary["channel"] {
  const normalized = channel.toLowerCase();

  if (normalized.includes("sip") || normalized.includes("voice")) {
    return "SIP";
  }

  if (normalized.includes("telegram")) {
    return "Telegram";
  }

  return "Widget";
}

function mapDashboardOverview(payload: CoreDashboardResponse): DashboardOverview {
  const automationRate = Math.round(payload.automation_rate * 100);

  return {
    kpis: [
      {
        label: "Диалоги",
        value: String(payload.conversations_total),
        detail: `Tenant: ${payload.tenant.name}`,
      },
      {
        label: "Automation rate",
        value: `${automationRate}%`,
        detail: "Resolved conversations / total conversations",
      },
      {
        label: "Агенты",
        value: String(payload.agents_total),
        detail: "Draft и published agents",
      },
      {
        label: "Knowledge sources",
        value: String(payload.knowledge_sources_total),
        detail: "Indexed sources in Core API",
      },
    ],
    alerts: [
      {
        title:
          payload.unresolved_topics_total > 0
            ? "Есть unresolved topics"
            : "Unresolved topics не найдены",
        tone: payload.unresolved_topics_total > 0 ? "warn" : "ok",
        description:
          payload.unresolved_topics_total > 0
            ? `${payload.unresolved_topics_total} тем требуют расширения базы знаний.`
            : "Core API не вернул нерешенных тем для demo tenant.",
      },
      {
        title: "Core API подключен",
        tone: "ok",
        description: `Данные загружены успешно.`,
      },
    ],
  };
}

function mapProductionReadiness(payload: CoreReadinessResponse): ProductionReadiness {
  return {
    status: payload.status,
    environment: payload.environment,
    storeBackend: payload.store_backend,
    providers: payload.providers.map((provider) => ({
      name: provider.provider,
      status: provider.status,
      detail: provider.detail,
    })),
  };
}

function mapAgent(agent: CoreAgent): Agent {
  return {
    channel: agent.channel,
    id: agent.id,
    name: agent.name,
    status: agent.status,
    channels: [formatChannel(agent.channel)],
    version: `v${agent.version}`,
    updatedAt: formatDateTime(agent.updated_at),
    goal: agent.prompt,
    voiceId: agent.voice_id || "alloy",
    voiceLanguage: agent.voice_language || "ru",
    voiceSpeed: agent.voice_speed || 1.0,
    temperature: agent.temperature || 0.3,
    maxTokens: agent.max_tokens || 1024,
    modelName: agent.model_name || "gpt-4o-mini",
  };
}

function mapSourceType(sourceType: string): KnowledgeSource["type"] {
  const normalized = sourceType.toLowerCase();

  if (normalized.includes("url") || normalized.includes("web")) {
    return "url";
  }

  if (normalized.includes("integration")) {
    return "integration";
  }

  return "file";
}

function sourceCoverageScore(source: CoreKnowledgeSource) {
  if (source.status === "indexed") {
    return 100;
  }

  if (source.status === "pending") {
    return 35;
  }

  return 0;
}

function mapKnowledgeSource(source: CoreKnowledgeSource): KnowledgeSource {
  return {
    id: source.id,
    name: source.title,
    type: mapSourceType(source.source_type),
    syncStatus: source.status,
    documents: source.chunk_count,
    coverageScore: sourceCoverageScore(source),
    updatedAt: formatDateTime(source.updated_at),
  };
}

function mapIngestionJob(job: CoreKnowledgeIngestionJob): KnowledgeIngestionJob {
  return {
    backend: job.background_backend,
    chunkCount: job.chunk_count,
    collection: job.qdrant_collection,
    errorMessage: job.error_message ?? undefined,
    id: job.id,
    sourceId: job.source_id,
    status: job.status,
    updatedAt: formatDateTime(job.updated_at),
  };
}

function mapConversation(conversation: CoreConversation): ConversationSummary {
  return {
    id: conversation.id,
    channel: formatChannel(conversation.channel),
    customer: "Клиент",
    status: conversation.status,
    summary: conversation.summary || "Диалог без summary",
    latency: "—",
    updatedAt: formatDateTime(conversation.updated_at),
  };
}

function mapConversationDetail(payload: CoreConversationDetail): ConversationDetail {
  const sourceNames = new Map(payload.sources.map((source) => [source.id, source.title]));
  const customerMessage = payload.messages.find((message) => message.role === "customer");
  const conversation = mapConversation(payload.conversation);

  return {
    ...conversation,
    customer: customerMessage ? "Клиент Core API" : conversation.customer,
    resolution: payload.conversation.resolution_status,
    handoffReason:
      payload.conversation.status === "escalated" ? payload.conversation.resolution_status : undefined,
    messages: payload.messages.map((message) => ({
      id: message.id,
      role: message.role,
      content: message.content,
      createdAt: formatDateTime(message.created_at),
      sources: message.source_ids
        .map((sourceId) => sourceNames.get(sourceId))
        .filter((sourceName): sourceName is string => Boolean(sourceName)),
    })),
    tools: [],
  };
}

function conversationSummaries(): ConversationSummary[] {
  return conversations.map((conversation) => ({
    id: conversation.id,
    channel: conversation.channel,
    customer: conversation.customer,
    status: conversation.status,
    summary: conversation.summary,
    latency: conversation.latency,
    updatedAt: conversation.updatedAt,
  }));
}

type TenantSettings = Record<string, unknown>;

export async function getTenantSettings(): Promise<ApiResult<TenantSettings>> {
  const tenantId = await getCoreTenantId();
  return fetchMappedCoreData<TenantSettings, TenantSettings>(
    `/api/v1/tenants/${tenantId}/settings`,
    {},
    (payload) => payload,
  );
}

export async function getOnboardingItems(): Promise<OnboardingItem[]> {
  const [agentsRes, sourcesRes, conversationsRes, settingsRes] = await Promise.all([
    getAgents(),
    getKnowledgeSources(),
    getConversations(),
    getTenantSettings().catch(() => ({
      data: {} as TenantSettings,
      path: "",
      state: "error" as const,
    })),
  ]);

  const stats = {
    agentsTotal: agentsRes.state === "live" ? agentsRes.data.length : 0,
    sourcesTotal: sourcesRes.state === "live" ? sourcesRes.data.length : 0,
    conversationsTotal: conversationsRes.state === "live" ? conversationsRes.data.length : 0,
  };

  const hasPublishedAgent = agentsRes.state === "live" && agentsRes.data.some(a => a.status === "published");
  const settings = settingsRes.data || {};
  const hasTelegramToken = !!settings.telegram_bot_token;

  const getStepStatus = (stepId: string): "done" | "current" | "blocked" | "pending" => {
    if (stepId === "tenant") {
      return "done";
    }
    if (stepId === "agent") {
      return stats.agentsTotal > 0 ? "done" : "current";
    }
    if (stepId === "knowledge") {
      if (stats.agentsTotal === 0) return "pending";
      return stats.sourcesTotal > 0 ? "done" : "current";
    }
    if (stepId === "conversation") {
      if (stats.sourcesTotal === 0) return "pending";
      return stats.conversationsTotal > 0 ? "done" : "current";
    }
    if (stepId === "publish") {
      if (stats.conversationsTotal === 0) return "pending";
      return hasPublishedAgent ? "done" : "current";
    }
    if (stepId === "telegram") {
      if (!hasPublishedAgent) return "pending";
      return hasTelegramToken ? "done" : "current";
    }
    if (stepId === "widget") {
      if (!hasPublishedAgent) return "pending";
      return "current";
    }
    return "pending";
  };

  return [
    {
      id: "tenant",
      title: "Создать tenant и профиль бизнеса",
      description: "Базовая регистрация, язык, отрасль, timezone и SLA ожидания.",
      status: getStepStatus("tenant"),
      href: "/onboarding",
    },
    {
      id: "agent",
      title: "Собрать draft агента",
      description: "Prompt, policy, каналы, handoff rules и первая версия сценария.",
      status: getStepStatus("agent"),
      href: "/agents/new",
    },
    {
      id: "knowledge",
      title: "Загрузить knowledge source",
      description: "Меню, FAQ или URL для mock RAG ответа с attribution.",
      status: getStepStatus("knowledge"),
      href: "/knowledge",
    },
    {
      id: "conversation",
      title: "Пройти тестовый диалог",
      description: "Проверить ответ, sources, latency, summary и conversation log.",
      status: getStepStatus("conversation"),
      href: "/test-console",
    },
    {
      id: "publish",
      title: "Опубликовать MVP канал",
      description: "Публикация доступна из карточки агента и страницы редактирования.",
      status: getStepStatus("publish"),
      href: "/agents",
    },
    {
      id: "telegram",
      title: "Подключить Telegram бота",
      description: "Получите токен в @BotFather и укажите его в настройках канала Telegram.",
      status: getStepStatus("telegram"),
      href: "/settings/channels",
    },
    {
      id: "widget",
      title: "Установить Web Widget",
      description: "Скопируйте snippet <script src=\"...\"> на свой сайт для запуска чата.",
      status: getStepStatus("widget"),
      href: "/dashboard",
    },
  ];
}

export async function getDashboardOverview(): Promise<ApiResult<DashboardOverview>> {
  const tenantId = await getCoreTenantId();

  return fetchMappedCoreData(
    `/api/v1/tenants/${tenantId}/dashboard`,
    dashboardOverview,
    mapDashboardOverview,
  );
}

export function getProductionReadiness(): Promise<ApiResult<ProductionReadiness>> {
  return fetchMappedCoreData("/api/v1/readiness", productionReadiness, mapProductionReadiness);
}

export function getAgents(): Promise<ApiResult<Agent[]>> {
  return fetchMappedCoreData("/api/v1/agents", agents, (payload: CoreAgent[]) => payload.map(mapAgent));
}

export function getAgent(agentId: string): Promise<ApiResult<Agent | null>> {
  const path = `/api/v1/agents/${agentId}`;
  const fallback = agents.find((agent) => agent.id === agentId) ?? null;

  return fetchMappedCoreData(path, fallback, mapAgent);
}

export function getKnowledgeSources(): Promise<ApiResult<KnowledgeSource[]>> {
  return fetchMappedCoreData("/api/v1/knowledge/sources", knowledgeSources, (payload: CoreKnowledgeSource[]) =>
    payload.map(mapKnowledgeSource),
  );
}

export function getKnowledgeIngestionJobs(): Promise<ApiResult<KnowledgeIngestionJob[]>> {
  return fetchMappedCoreData(
    "/api/v1/knowledge/ingestion/jobs",
    ingestionJobs,
    (payload: CoreKnowledgeIngestionJob[]) => payload.map(mapIngestionJob),
  );
}

export function getConversations(): Promise<ApiResult<ConversationSummary[]>> {
  return fetchMappedCoreData("/api/v1/conversations", conversationSummaries(), (payload: CoreConversation[]) =>
    payload.map(mapConversation),
  );
}

export function getConversationDetail(conversationId: string): Promise<ApiResult<ConversationDetail | null>> {
  const path = `/api/v1/conversations/${conversationId}`;
  const fallback = conversations.find((conversation) => conversation.id === conversationId) ?? null;

  return fetchMappedCoreData(path, fallback, mapConversationDetail);
}
