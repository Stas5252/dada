import { getAccessToken } from "./auth";

export type CoreApiState = "live" | "mock" | "error";

export type CoreApiFetchResult<T> =
  | {
      data: T;
      message?: string;
      path: string;
      state: "live";
    }
  | {
      message: string;
      path: string;
      state: "mock" | "error";
    };

export type CoreApiMutationResult<T> =
  | {
      data: T;
      path: string;
      state: "live";
    }
  | {
      message: string;
      path: string;
      state: "error";
    };

export type CoreTokenPairResponse = {
  access_token: string;
  refresh_token: string;
  access_expires_at: string;
  refresh_expires_at: string;
  requires_mfa?: boolean;
};

export type CoreTenant = {
  created_at: string;
  id: string;
  name: string;
  plan: string;
  status: "active" | "suspended";
  updated_at: string;
};

export type CoreUser = {
  created_at: string;
  email: string;
  email_verified: boolean;
  id: string;
  mfa_enabled: boolean;
  mfa_recovery_codes_remaining: number;
  name: string;
  role: "owner" | "admin" | "agent" | "viewer";
  tenant_id: string;
  updated_at: string;
};

export type CoreMfaSetupResponse = {
  provisioning_uri: string;
  secret: string;
};

export type CoreAuditLog = {
  id: string;
  tenant_id: string | null;
  user_id: string | null;
  event_type: string;
  ip_address: string | null;
  details: Record<string, string>;
  created_at: string;
  updated_at: string;
};

export type CoreMfaRecoveryCodesResponse = {
  codes: string[];
  remaining: number;
};

export type CoreGuardrailPolicySettings = {
  enabled: boolean;
  opt_out_enabled: boolean;
  human_handoff_enabled: boolean;
  regulated_topics_enabled: boolean;
  prompt_injection_block_enabled: boolean;
  toxicity_escalation_enabled: boolean;
  outbound_safety_enabled: boolean;
  tool_safety_enabled: boolean;
  ai_disclosure_required: boolean;
  custom_regulated_terms: string[];
  custom_prohibited_claims: string[];
};

export type CoreChannelAutomationMode = "autopilot" | "draft_only" | "human_approval";

export type CoreChannelCompliancePolicySettings = {
  mode: CoreChannelAutomationMode;
  outbound_enabled: boolean;
  ai_disclosure_required: boolean;
  require_opt_out_notice: boolean;
  require_contact_consent_for_outbound: boolean;
  max_auto_replies_per_conversation: number;
};

export type CoreChannelPoliciesSettings = {
  default_policy: CoreChannelCompliancePolicySettings;
  web_widget: CoreChannelCompliancePolicySettings;
  telegram: CoreChannelCompliancePolicySettings;
  vk: CoreChannelCompliancePolicySettings;
  whatsapp: CoreChannelCompliancePolicySettings;
  voice: CoreChannelCompliancePolicySettings;
};

export type CoreDashboardResponse = {
  agents_total: number;
  automation_rate: number;
  conversations_total: number;
  knowledge_sources_total: number;
  tenant: CoreTenant;
  unresolved_topics_total: number;
};

export type CoreBillingStatus = {
  plan: string;
  messages_used: number;
  messages_limit: number;
  messages_remaining: number;
  billing_period_start: string;
  limit_exceeded: boolean;
  conversations_used: number;
};

export type CoreAgent = {
  channel: string;
  created_at: string;
  id: string;
  name: string;
  prompt: string;
  status: "draft" | "published" | "archived";
  tenant_id: string;
  updated_at: string;
  version: number;
  voice_id: string;
  voice_language: string;
  voice_speed: number;
  temperature: number;
  max_tokens: number;
  model_name: string;
}

export type CoreTestbedReadinessStatus = "ready" | "action_required";

export type CoreTestbedCaseReadinessStatus = "passed" | "failed" | "running" | "stale_run" | "missing_run";

export type CoreTestbedLatestRunSummary = {
  id: string;
  status: "running" | "passed" | "failed";
  result_summary: string | null;
  created_at: string;
  updated_at: string;
};

export type CoreTestbedCaseReadiness = {
  test_case_id: string;
  test_case_name: string;
  status: CoreTestbedCaseReadinessStatus;
  latest_run: CoreTestbedLatestRunSummary | null;
  required_action: string | null;
};

export type CoreTestbedPublishFailure = {
  code: string;
  message: string;
  test_case_id?: string;
  test_case_name?: string;
  latest_run_id?: string;
  latest_run_status?: "running" | "passed" | "failed";
};

export type CoreTestbedReadinessResponse = {
  agent_id: string;
  checked_at: string;
  status: CoreTestbedReadinessStatus;
  publish_blocked: boolean;
  required_pass_rate: number;
  minimum_test_cases: number;
  total_cases: number;
  passing_cases: number;
  failing_cases: number;
  running_cases: number;
  stale_cases: number;
  missing_run_cases: number;
  pass_rate: number;
  failures: CoreTestbedPublishFailure[];
  cases: CoreTestbedCaseReadiness[];
};

export type CorePathway = {
  nodes: Record<string, unknown>[] | null;
  edges: Record<string, unknown>[] | null;
};

export type CoreKnowledgeSource = {
  chunk_count: number;
  content: string;
  created_at: string;
  id: string;
  source_type: string;
  status: "pending" | "indexed" | "failed";
  tenant_id: string;
  title: string;
  updated_at: string;
};

export type CoreKnowledgeIngestionJob = {
  background_backend: string;
  chunk_count: number;
  created_at: string;
  error_message: string | null;
  id: string;
  idempotency_key: string;
  qdrant_collection: string;
  source_id: string;
  status: "queued" | "running" | "completed" | "failed";
  tenant_id: string;
  updated_at: string;
};

export type CoreRagEvalStatus = "passed" | "failed";

export type CoreRagEvalCaseResult = {
  name: string;
  status: CoreRagEvalStatus;
  query: string;
  should_answer: boolean;
  retrieved_source_titles: string[];
  citation_titles: string[];
  matched_expected_terms: string[];
  missing_expected_terms: string[];
  no_answer_respected: boolean;
  relevance_score: number;
  answer_preview: string;
  failures: string[];
};

export type CoreRagEvalResponse = {
  status: CoreRagEvalStatus;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  pass_rate: number;
  required_pass_rate: number;
  min_relevance_score: number;
  results: CoreRagEvalCaseResult[];
};

export type CoreConversation = {
  agent_id: string;
  channel: string;
  created_at: string;
  id: string;
  resolution_status: string;
  status: "open" | "resolved" | "escalated";
  summary: string;
  tenant_id: string;
  updated_at: string;
};

export type CoreMessage = {
  confidence: number | null;
  content: string;
  conversation_id: string;
  created_at: string;
  id: string;
  role: "customer" | "agent" | "operator" | "system";
  source_ids: string[];
  tenant_id: string;
  updated_at: string;
};

export type CoreConversationDetail = {
  conversation: CoreConversation;
  messages: CoreMessage[];
  sources: CoreKnowledgeSource[];
};

export type CoreChatMessageResponse = {
  agent_message: CoreMessage;
  conversation: CoreConversation;
  customer_message: CoreMessage;
  sources: CoreKnowledgeSource[];
};

export type CoreVoicePreviewTurnResponse = {
  assistant_text: string;
  conversation_id: string;
  customer_text: string;
  session: {
    pending_confirmation_id: string | null;
    session_id: string;
    state:
      | "new"
      | "listening"
      | "thinking"
      | "speaking"
      | "waiting_confirmation"
      | "handoff"
      | "ended";
    tenant_id: string;
    transcript: Array<{
      speaker: string;
      text: string;
    }>;
  };
  tts_status: "not_requested" | "not_configured";
};

export type CoreProviderReadiness = {
  detail: string;
  provider: string;
  status: "configured" | "missing_secret" | "local_stub";
};

export type CoreIntegrationReadinessStatus = "configured" | "local_stub" | "needs_setup";

export type CoreIntegrationReadinessItem = {
  key: string;
  label: string;
  category: string;
  status: CoreIntegrationReadinessStatus;
  summary: string;
  required_settings: string[];
  configured_settings: string[];
  missing_settings: string[];
  setup_url: string | null;
  docs_url: string | null;
  blocking: boolean;
};

export type CoreIntegrationReadinessResponse = {
  status: "ready" | "mock_mode" | "action_required";
  checked_at: string;
  items: CoreIntegrationReadinessItem[];
};

export type CoreChannelWebhookDiagnosticStatus = "ready" | "warning" | "needs_setup";

export type CoreChannelWebhookPublicUrlStatus = "https_ready" | "local_only" | "missing";

export type CoreChannelWebhookDiagnosticItem = {
  key: string;
  label: string;
  provider: string;
  status: CoreChannelWebhookDiagnosticStatus;
  summary: string;
  inbound_webhook_url: string | null;
  required_settings: string[];
  configured_settings: string[];
  missing_settings: string[];
  setup_steps: string[];
  security_notes: string[];
  warnings: string[];
  setup_url: string | null;
  docs_url: string | null;
  test_mode: boolean;
};

export type CoreChannelWebhookDiagnosticsResponse = {
  checked_at: string;
  public_base_url: string;
  public_url_status: CoreChannelWebhookPublicUrlStatus;
  items: CoreChannelWebhookDiagnosticItem[];
};

export type CoreReadinessResponse = {
  checked_at: string;
  environment: string;
  providers: CoreProviderReadiness[];
  service: string;
  status: "ready" | "degraded";
  store_backend: string;
};

export type CoreChannelBreakdown = {
  channel: string;
  count: number;
};

export type CoreDailyConversation = {
  date: string;
  count: number;
};

export type CoreUnresolvedTopic = {
  question: string;
  count: number;
  last_seen: string;
};

export type CoreAnalyticsOverview = {
  total_conversations: number;
  resolved: number;
  escalated: number;
  open: number;
  automation_rate: number;
  total_agents: number;
  active_agents: number;
  total_knowledge_sources: number;
  total_messages: number;
  avg_messages_per_conversation: number;
  conversations_by_channel: CoreChannelBreakdown[];
  conversations_by_day: CoreDailyConversation[];
  top_unresolved: CoreUnresolvedTopic[];
};

export type CoreAgentStats = {
  agent_id: string;
  agent_name: string;
  status: string;
  total_conversations: number;
  resolved: number;
  escalated: number;
  automation_rate: number;
};


const CORE_API_PREFIX = "api/v1";
const LOCAL_DEMO_TENANT_ID = "00000000-0000-0000-0000-000000000001";

function assertServerRuntime() {
  if (typeof window !== "undefined") {
    throw new Error("Core API client must be used from server components or server actions.");
  }
}

function trimTrailingSlashes(value: string) {
  return value.replace(/\/+$/, "");
}

function getCoreApiBaseUrl() {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL?.trim();

  return baseUrl ? trimTrailingSlashes(baseUrl) : null;
}

export async function getCoreTenantId() {
  let tenantIdFromToken: string | undefined;
  try {
    const token = await getAccessToken();
    if (token) {
      const payloadBase64 = token.split(".")[1];
      if (payloadBase64) {
        const payloadJson = Buffer.from(payloadBase64, "base64url").toString("utf8");
        const payload = JSON.parse(payloadJson);
        tenantIdFromToken = payload.tenant_id;
      }
    }
  } catch {
    // Ignore decode errors
  }

  return (
    tenantIdFromToken ||
    process.env.NEXT_PUBLIC_TENANT_ID?.trim() ||
    process.env.NEXT_PUBLIC_DEMO_TENANT_ID?.trim() ||
    LOCAL_DEMO_TENANT_ID
  );
}

function buildCoreApiUrl(baseUrl: string, path: string) {
  const url = new URL(`${baseUrl}/`);
  const basePath = trimTrailingSlashes(url.pathname);
  const requestPath = path.replace(/^\/+/, "");
  const pathWithoutDuplicatePrefix =
    basePath.endsWith(`/${CORE_API_PREFIX}`) && requestPath.startsWith(`${CORE_API_PREFIX}/`)
      ? requestPath.slice(CORE_API_PREFIX.length + 1)
      : requestPath;

  url.pathname = [basePath, pathWithoutDuplicatePrefix].filter(Boolean).join("/");

  return url;
}

export async function fetchCoreApi<T>(path: string): Promise<CoreApiFetchResult<T>> {
  assertServerRuntime();

  const baseUrl = getCoreApiBaseUrl();

  if (!baseUrl) {
    return {
      state: "mock",
      path,
      message: "NEXT_PUBLIC_API_URL не задан, показаны mock данные MVP.",
    };
  }

  try {
    const token = await getAccessToken();
    const headers: Record<string, string> = {
      Accept: "application/json",
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(buildCoreApiUrl(baseUrl, path), {
      cache: "no-store",
      headers,
    });

    if (!response.ok) {
      return {
        state: "error",
        path,
        message: `Core API вернул ${response.status}. Показаны fallback данные.`,
      };
    }

    return {
      data: (await response.json()) as T,
      state: "live",
      path,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Неизвестная ошибка API";

    return {
      state: "error",
      path,
      message: `Не удалось получить Core API данные: ${message}. Показаны fallback данные.`,
    };
  }
}

export async function mutateCoreApi<T>(
  path: string,
  payload: Record<string, unknown>,
): Promise<CoreApiMutationResult<T>> {
  assertServerRuntime();

  const baseUrl = getCoreApiBaseUrl();

  if (!baseUrl) {
    return {
      state: "error",
      path,
      message: "NEXT_PUBLIC_API_URL не задан, live mutation не выполнена.",
    };
  }

  try {
    const token = await getAccessToken();
    const headers: Record<string, string> = {
      Accept: "application/json",
      "Content-Type": "application/json",
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(buildCoreApiUrl(baseUrl, path), {
      body: JSON.stringify(payload),
      cache: "no-store",
      headers,
      method: "POST",
    });

    if (!response.ok) {
      return {
        state: "error",
        path,
        message: `Core API вернул ${response.status}.`,
      };
    }

    return {
      state: "live",
      path,
      data: (await response.json()) as T,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Неизвестная ошибка API";

    return {
      state: "error",
      path,
      message: `Не удалось выполнить Core API mutation: ${message}.`,
    };
  }
}

export async function patchCoreApi<T>(
  path: string,
  payload: Record<string, unknown>,
): Promise<CoreApiMutationResult<T>> {
  assertServerRuntime();

  const baseUrl = getCoreApiBaseUrl();

  if (!baseUrl) {
    return {
      state: "error",
      path,
      message: "NEXT_PUBLIC_API_URL не задан, live mutation не выполнена.",
    };
  }

  try {
    const token = await getAccessToken();
    const headers: Record<string, string> = {
      Accept: "application/json",
      "Content-Type": "application/json",
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(buildCoreApiUrl(baseUrl, path), {
      body: JSON.stringify(payload),
      cache: "no-store",
      headers,
      method: "PATCH",
    });

    if (!response.ok) {
      return {
        state: "error",
        path,
        message: `Core API вернул ${response.status}.`,
      };
    }

    return {
      state: "live",
      path,
      data: (await response.json()) as T,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Неизвестная ошибка API";

    return {
      state: "error",
      path,
      message: `Не удалось выполнить Core API patch: ${message}.`,
    };
  }
}

export async function mutateCoreApiNoContent(
  path: string,
  payload: Record<string, unknown>,
): Promise<CoreApiMutationResult<null>> {
  assertServerRuntime();

  const baseUrl = getCoreApiBaseUrl();

  if (!baseUrl) {
    return {
      state: "error",
      path,
      message: "NEXT_PUBLIC_API_URL не задан, live mutation не выполнена.",
    };
  }

  try {
    const token = await getAccessToken();
    const headers: Record<string, string> = {
      Accept: "application/json",
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(buildCoreApiUrl(baseUrl, path), {
      body: JSON.stringify(payload),
      cache: "no-store",
      headers,
      method: "POST",
    });

    if (!response.ok) {
      return {
        state: "error",
        path,
        message: `Core API вернул ${response.status}.`,
      };
    }

    return {
      data: null,
      path,
      state: "live",
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Неизвестная ошибка API";

    return {
      state: "error",
      path,
      message: `Не удалось выполнить Core API mutation: ${message}.`,
    };
  }
}

export async function revokeRefreshToken(refreshToken: string): Promise<CoreApiMutationResult<null>> {
  assertServerRuntime();

  const baseUrl = getCoreApiBaseUrl();
  const path = "/api/v1/auth/logout";

  if (!baseUrl) {
    return {
      state: "error",
      path,
      message: "NEXT_PUBLIC_API_URL не задан, refresh session не отозвана.",
    };
  }

  try {
    const response = await fetch(buildCoreApiUrl(baseUrl, path), {
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      method: "POST",
    });

    if (!response.ok) {
      return {
        state: "error",
        path,
        message: `Core API вернул ${response.status}.`,
      };
    }

    return {
      data: null,
      path,
      state: "live",
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Неизвестная ошибка API";

    return {
      state: "error",
      path,
      message: `Не удалось отозвать refresh session: ${message}.`,
    };
  }
}

export async function uploadCoreApi<T>(
  path: string,
  formData: FormData,
): Promise<CoreApiMutationResult<T>> {
  assertServerRuntime();

  const baseUrl = getCoreApiBaseUrl();

  if (!baseUrl) {
    return {
      state: "error",
      path,
      message: "NEXT_PUBLIC_API_URL не задан, live mutation не выполнена.",
    };
  }

  try {
    const token = await getAccessToken();
    const headers: Record<string, string> = {
      Accept: "application/json",
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(buildCoreApiUrl(baseUrl, path), {
      body: formData,
      cache: "no-store",
      headers,
      method: "POST",
    });

    if (!response.ok) {
      return {
        state: "error",
        path,
        message: `Core API вернул ${response.status}.`,
      };
    }

    return {
      data: (await response.json()) as T,
      state: "live",
      path,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Неизвестная ошибка API";

    return {
      state: "error",
      path,
      message: `Не удалось выполнить Core API upload: ${message}.`,
    };
  }
}

export async function deleteCoreApiNoContent(
  path: string,
): Promise<CoreApiMutationResult<null>> {
  assertServerRuntime();

  const baseUrl = getCoreApiBaseUrl();

  if (!baseUrl) {
    return {
      state: "error",
      path,
      message: "NEXT_PUBLIC_API_URL не задан, live mutation не выполнена.",
    };
  }

  try {
    const token = await getAccessToken();
    const headers: Record<string, string> = {
      Accept: "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(buildCoreApiUrl(baseUrl, path), {
      cache: "no-store",
      headers,
      method: "DELETE",
    });

    if (!response.ok) {
      return {
        state: "error",
        path,
        message: `Core API вернул ${response.status}.`,
      };
    }

    return {
      data: null,
      path,
      state: "live",
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Неизвестная ошибка API";

    return {
      state: "error",
      path,
      message: `Не удалось выполнить Core API delete: ${message}.`,
    };
  }
}
