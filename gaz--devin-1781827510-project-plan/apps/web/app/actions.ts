"use server";

import { randomUUID } from "crypto";
import { redirect } from "next/navigation";
import type { CoreTokenPairResponse } from "../lib/auth";
import {
  mutateCoreApi,
  mutateCoreApiNoContent,
  patchCoreApi,
  revokeRefreshToken,
  uploadCoreApi,
  getCoreTenantId,
  deleteCoreApiNoContent,
  type CoreAgent,
  type CoreChatMessageResponse,
  type CoreKnowledgeIngestionJob,
  type CoreKnowledgeSource,
  type CoreMfaRecoveryCodesResponse,
  type CoreMfaSetupResponse,
  type CoreVoicePreviewTurnResponse,
} from "../lib/core-api";

function textValue(formData: FormData, key: string) {
  const value = formData.get(key);

  return typeof value === "string" ? value.trim() : "";
}

function noticePath(path: string, notice: string) {
  const params = new URLSearchParams({ notice });

  return `${path}?${params.toString()}`;
}

function safeAgentReturnPath(path: string) {
  return path.startsWith("/agents") ? path : "/agents";
}

function isMfaCode(value: string) {
  const recoveryCode = value.replace(/[\s-]/g, "");

  return /^\d{6}$/.test(value) || /^[A-Z0-9]{8}$/i.test(recoveryCode);
}

export async function createAgentAction(formData: FormData) {
  const name = textValue(formData, "name");
  const channel = textValue(formData, "channel") || "telegram";
  const prompt = textValue(formData, "prompt");
  const voice_id = textValue(formData, "voice_id") || "alloy";
  const voice_language = textValue(formData, "voice_language") || "ru";
  const voice_speed = parseFloat(textValue(formData, "voice_speed") || "1.0");
  const temperature = parseFloat(textValue(formData, "temperature") || "0.3");
  const max_tokens = parseInt(textValue(formData, "max_tokens") || "1024", 10);
  const model_name = textValue(formData, "model_name") || "gpt-4o-mini";

  if (!name || prompt.length < 10) {
    redirect(noticePath("/agents/new", "agent-invalid"));
  }

  const result = await mutateCoreApi<CoreAgent>("/api/v1/agents", {
    channel,
    name,
    prompt,
    voice_id,
    voice_language,
    voice_speed,
    temperature,
    max_tokens,
    model_name,
  });

  if (result.state === "live") {
    redirect(noticePath("/agents", "agent-created"));
  }

  redirect(noticePath("/agents/new", "agent-error"));
}

export async function updateAgentAction(formData: FormData) {
  const agentId = textValue(formData, "agent_id");
  const name = textValue(formData, "name");
  const channel = textValue(formData, "channel") || "telegram";
  const prompt = textValue(formData, "prompt");
  const voice_id = textValue(formData, "voice_id") || "alloy";
  const voice_language = textValue(formData, "voice_language") || "ru";
  const voice_speed = parseFloat(textValue(formData, "voice_speed") || "1.0");
  const temperature = parseFloat(textValue(formData, "temperature") || "0.3");
  const max_tokens = parseInt(textValue(formData, "max_tokens") || "1024", 10);
  const model_name = textValue(formData, "model_name") || "gpt-4o-mini";
  const returnTo = safeAgentReturnPath(textValue(formData, "return_to") || `/agents/${agentId}`);

  if (!agentId || !name || prompt.length < 10) {
    redirect(noticePath(returnTo, "agent-invalid"));
  }

  const result = await patchCoreApi<CoreAgent>(`/api/v1/agents/${agentId}`, {
    channel,
    name,
    prompt,
    voice_id,
    voice_language,
    voice_speed,
    temperature,
    max_tokens,
    model_name,
  });

  if (result.state === "live") {
    redirect(noticePath(`/agents/${result.data.id}`, "agent-updated"));
  }

  redirect(noticePath(returnTo, "agent-update-error"));
}

export async function publishAgentAction(formData: FormData) {
  const agentId = textValue(formData, "agent_id");
  const returnTo = safeAgentReturnPath(textValue(formData, "return_to") || "/agents");

  if (!agentId) {
    redirect(noticePath(returnTo, "agent-publish-error"));
  }

  const result = await mutateCoreApi<CoreAgent>(`/api/v1/agents/${agentId}/publish`, {});

  if (result.state === "live") {
    redirect(noticePath(returnTo, "agent-published"));
  }

  redirect(noticePath(returnTo, "agent-publish-error"));
}

export async function createKnowledgeSourceAction(formData: FormData) {
  const sourceType = textValue(formData, "source_type") || "manual";

  if (sourceType === "file") {
    const file = formData.get("file") as File;
    if (!file || file.size === 0) {
      redirect(noticePath("/knowledge", "knowledge-invalid-file"));
    }

    const uploadForm = new FormData();
    uploadForm.append("file", file);

    const result = await uploadCoreApi<CoreKnowledgeSource>("/api/v1/knowledge/upload", uploadForm);

    if (result.state === "live") {
      redirect(noticePath("/knowledge", "knowledge-created"));
    }

    redirect(noticePath("/knowledge", "knowledge-error"));
  }

  if (sourceType === "url") {
    const title = textValue(formData, "title");
    if (!title || !title.startsWith("http")) {
      redirect(noticePath("/knowledge", "knowledge-invalid"));
    }
    const result = await mutateCoreApi<CoreKnowledgeSource>("/api/v1/knowledge/upload-url", {
      url: title,
    });
    if (result.state === "live") {
      redirect(noticePath("/knowledge", "knowledge-created"));
    }
    redirect(noticePath("/knowledge", "knowledge-error"));
  }

  const title = textValue(formData, "title");
  const content = textValue(formData, "content");

  if (!title || content.length < 2) {
    redirect(noticePath("/knowledge", "knowledge-invalid"));
  }

  const result = await mutateCoreApi<CoreKnowledgeSource>("/api/v1/knowledge/sources", {
    content,
    source_type: sourceType,
    title,
  });

  if (result.state === "live") {
    redirect(noticePath("/knowledge", "knowledge-created"));
  }

  redirect(noticePath("/knowledge", "knowledge-error"));
}

export async function reingestKnowledgeSourceAction(formData: FormData) {
  const sourceId = textValue(formData, "source_id");

  if (!sourceId) {
    redirect(noticePath("/knowledge", "knowledge-reingest-error"));
  }

  const result = await mutateCoreApi<CoreKnowledgeIngestionJob>(
    `/api/v1/knowledge/sources/${sourceId}/ingest`,
    {},
  );

  if (result.state === "live") {
    redirect(noticePath("/knowledge", "knowledge-reingested"));
  }

  redirect(noticePath("/knowledge", "knowledge-reingest-error"));
}

export async function createMockChatAction(formData: FormData) {
  const agentId = textValue(formData, "agent_id");
  const channel = textValue(formData, "channel") || "web_widget";
  const message = textValue(formData, "message");

  if (!agentId || !message) {
    redirect(noticePath("/test-console", "chat-invalid"));
  }

  const result = await mutateCoreApi<CoreChatMessageResponse>("/api/v1/chat/mock", {
    agent_id: agentId,
    channel,
    message,
  });

  if (result.state === "live") {
    redirect(noticePath(`/conversations/${result.data.conversation.id}`, "chat-created"));
  }

  redirect(noticePath("/test-console", "chat-error"));
}

export async function createVoicePreviewAction(formData: FormData) {
  const agentId = textValue(formData, "agent_id");
  const message = textValue(formData, "message");
  const sessionId = textValue(formData, "session_id") || `voice-preview-${randomUUID()}`;

  if (!agentId || !message) {
    redirect(noticePath("/test-console", "voice-preview-invalid"));
  }

  const result = await mutateCoreApi<CoreVoicePreviewTurnResponse>(
    `/api/v1/voice/sessions/${encodeURIComponent(sessionId)}/preview-turn`,
    {
      agent_id: agentId,
      text: message,
    },
  );

  if (result.state === "live") {
    redirect(noticePath(`/conversations/${result.data.conversation_id}`, "voice-preview-created"));
  }

  redirect(noticePath("/test-console", "voice-preview-error"));
}

export async function loginAction(formData: FormData) {
  const email = textValue(formData, "email");
  const password = textValue(formData, "password");

  if (!email || !password) {
    redirect(noticePath("/login", "auth-invalid"));
  }

  const result = await mutateCoreApi<CoreTokenPairResponse>("/api/v1/auth/login", { email, password });

  if (result.state === "live" && result.data.access_token) {
    if (result.data.requires_mfa) {
      const { setMfaToken } = await import("../lib/auth");
      await setMfaToken(result.data.access_token, result.data.access_expires_at);
      redirect("/login/mfa");
    } else {
      const { setAuthCookies } = await import("../lib/auth");
      await setAuthCookies(result.data);
      redirect("/dashboard");
    }
  }

  redirect(noticePath("/login", "auth-error"));
}

export async function loginMfaAction(formData: FormData) {
  const code = textValue(formData, "code");
  if (!isMfaCode(code)) {
    redirect(noticePath("/login/mfa", "mfa-invalid"));
  }

  const { getMfaToken, clearMfaToken, setAuthCookies } = await import("../lib/auth");
  const token = await getMfaToken();

  if (!token) {
    redirect("/login");
  }

  const result = await mutateCoreApi<CoreTokenPairResponse>("/api/v1/auth/login/mfa", { token, code });

  if (result.state === "live" && result.data.access_token) {
    await clearMfaToken();
    await setAuthCookies(result.data);
    redirect("/dashboard");
  }

  redirect(noticePath("/login/mfa", "mfa-error"));
}

export async function registerAction(formData: FormData) {
  const companyName = textValue(formData, "company_name");
  const ownerEmail = textValue(formData, "owner_email");
  const ownerName = textValue(formData, "owner_name");
  const password = textValue(formData, "password");

  if (!companyName || !ownerEmail || !ownerName || password.length < 8) {
    redirect(noticePath("/register", "auth-invalid"));
  }

  const result = await mutateCoreApi<CoreTokenPairResponse>("/api/v1/auth/register", {
    company_name: companyName,
    owner_email: ownerEmail,
    owner_name: ownerName,
    password,
  });

  if (result.state === "live" && result.data.access_token) {
    const { setAuthCookies } = await import("../lib/auth");
    await setAuthCookies(result.data);
    redirect("/dashboard");
  }

  redirect(noticePath("/register", "auth-error"));
}

export async function requestPasswordResetAction(formData: FormData) {
  const email = textValue(formData, "email");

  if (!email) {
    redirect(noticePath("/forgot-password", "reset-invalid"));
  }

  const result = await mutateCoreApiNoContent("/api/v1/auth/request-password-reset", { email });

  if (result.state === "live") {
    redirect(noticePath("/forgot-password", "reset-sent"));
  }

  redirect(noticePath("/forgot-password", "reset-error"));
}

export async function resetPasswordAction(formData: FormData) {
  const token = textValue(formData, "token");
  const newPassword = textValue(formData, "new_password");
  const confirmPassword = textValue(formData, "confirm_password");

  if (!token || newPassword.length < 8 || newPassword !== confirmPassword) {
    const path = token
      ? `/reset-password?${new URLSearchParams({ token, notice: "reset-invalid" }).toString()}`
      : noticePath("/reset-password", "reset-invalid");

    redirect(path);
  }

  const result = await mutateCoreApiNoContent("/api/v1/auth/reset-password", {
    token,
    new_password: newPassword,
  });

  if (result.state === "live") {
    redirect(noticePath("/login", "password-reset"));
  }

  redirect(`/reset-password?${new URLSearchParams({ token, notice: "reset-error" }).toString()}`);
}

export async function startMfaSetupAction() {
  const result = await mutateCoreApi<CoreMfaSetupResponse>("/api/v1/auth/mfa/setup", {});

  if (result.state === "live") {
    const { setMfaSetup } = await import("../lib/auth");
    await setMfaSetup(result.data);
    redirect(noticePath("/settings/security", "mfa-started"));
  }

  redirect(noticePath("/settings/security", "mfa-start-error"));
}

export async function verifyMfaSetupAction(formData: FormData) {
  const code = textValue(formData, "code");

  if (!/^\d{6}$/.test(code)) {
    redirect(noticePath("/settings/security", "mfa-code-invalid"));
  }

  const { clearMfaSetup, getMfaSetup } = await import("../lib/auth");
  const setup = await getMfaSetup();

  if (!setup) {
    redirect(noticePath("/settings/security", "mfa-setup-missing"));
  }

  const result = await mutateCoreApi<CoreMfaRecoveryCodesResponse>("/api/v1/auth/mfa/verify", {
    code,
    secret: setup.secret,
  });

  if (result.state === "live") {
    const { setMfaRecoveryCodes } = await import("../lib/auth");
    await setMfaRecoveryCodes(result.data.codes);
    await clearMfaSetup();
    redirect(noticePath("/settings/security", "mfa-enabled"));
  }

  redirect(noticePath("/settings/security", "mfa-code-error"));
}

export async function regenerateMfaRecoveryCodesAction(formData: FormData) {
  const code = textValue(formData, "code");

  if (!isMfaCode(code)) {
    redirect(noticePath("/settings/security", "mfa-code-invalid"));
  }

  const result = await mutateCoreApi<CoreMfaRecoveryCodesResponse>(
    "/api/v1/auth/mfa/recovery-codes",
    { code },
  );

  if (result.state === "live") {
    const { setMfaRecoveryCodes } = await import("../lib/auth");
    await setMfaRecoveryCodes(result.data.codes);
    redirect(noticePath("/settings/security", "mfa-recovery-regenerated"));
  }

  redirect(noticePath("/settings/security", "mfa-recovery-error"));
}

export async function disableMfaAction(formData: FormData) {
  const code = textValue(formData, "code");

  if (!isMfaCode(code)) {
    redirect(noticePath("/settings/security", "mfa-code-invalid"));
  }

  const result = await mutateCoreApiNoContent("/api/v1/auth/mfa/disable", { code });

  if (result.state === "live") {
    const { clearMfaRecoveryCodes } = await import("../lib/auth");
    await clearMfaRecoveryCodes();
    redirect(noticePath("/settings/security", "mfa-disabled"));
  }

  redirect(noticePath("/settings/security", "mfa-disable-error"));
}

export async function clearMfaRecoveryCodesAction() {
  const { clearMfaRecoveryCodes } = await import("../lib/auth");
  await clearMfaRecoveryCodes();
  redirect("/settings/security");
}

export async function cancelMfaSetupAction() {
  const { clearMfaSetup } = await import("../lib/auth");
  await clearMfaSetup();
  redirect(noticePath("/settings/security", "mfa-cancelled"));
}

export async function logoutAction() {
  const { clearAuthCookies, getRefreshToken } = await import("../lib/auth");
  const refreshToken = await getRefreshToken();

  if (refreshToken) {
    await revokeRefreshToken(refreshToken);
  }

  await clearAuthCookies();
  redirect("/");
}

export async function updateTenantSettingsAction(formData: FormData) {
  const tenantId = await getCoreTenantId();
  if (!tenantId) {
    redirect(noticePath("/dashboard", "auth-error"));
  }

  const openai_api_key = textValue(formData, "openai_api_key");
  const telegram_bot_token = textValue(formData, "telegram_bot_token");
  const twilio_account_sid = textValue(formData, "twilio_account_sid");
  const twilio_auth_token = textValue(formData, "twilio_auth_token");
  const twilio_phone_number = textValue(formData, "twilio_phone_number");
  const yookassa_shop_id = textValue(formData, "yookassa_shop_id");
  const yookassa_secret_key = textValue(formData, "yookassa_secret_key");
  const sip_server = textValue(formData, "sip_server");
  const sip_provider = textValue(formData, "sip_provider");
  const sip_login = textValue(formData, "sip_login");
  const sip_password = textValue(formData, "sip_password");

  const whatsapp_token = textValue(formData, "whatsapp_token");
  const whatsapp_phone_number_id = textValue(formData, "whatsapp_phone_number_id");
  const whatsapp_verify_token = textValue(formData, "whatsapp_verify_token");
  const vk_group_token = textValue(formData, "vk_group_token");
  const vk_confirmation_code = textValue(formData, "vk_confirmation_code");
  const iiko_api_login = textValue(formData, "iiko_api_login");
  const iiko_organization_id = textValue(formData, "iiko_organization_id");
  const iiko_terminal_group_id = textValue(formData, "iiko_terminal_group_id");

  const settings = {
    openai_api_key,
    telegram_bot_token,
    twilio_account_sid,
    twilio_auth_token,
    twilio_phone_number,
    yookassa_shop_id,
    yookassa_secret_key,
    sip_server,
    sip_provider,
    sip_login,
    sip_password,
    whatsapp_token,
    whatsapp_phone_number_id,
    whatsapp_verify_token,
    vk_group_token,
    vk_confirmation_code,
    iiko_api_login,
    iiko_organization_id,
    iiko_terminal_group_id,
  };

  const result = await mutateCoreApi<Record<string, object>>(`/api/v1/tenants/${tenantId}/settings`, {
    settings,
  });

  if (result.state === "live") {
    redirect(noticePath("/settings/channels", "settings-updated"));
  }

  redirect(noticePath("/settings/channels", "settings-error"));
}

export async function connectTelegramAction(formData: FormData) {
  const agentId = textValue(formData, "agent_id");
  const botToken = textValue(formData, "bot_token");
  const returnTo = safeAgentReturnPath(textValue(formData, "return_to") || `/agents/${agentId}`);

  if (!agentId || !botToken) {
    redirect(noticePath(returnTo, "telegram-invalid-token"));
  }

  const result = await mutateCoreApi<CoreAgent>(`/api/v1/agents/${agentId}/telegram/connect`, {
    bot_token: botToken,
  });

  if (result.state === "live") {
    redirect(noticePath(returnTo, "telegram-connected"));
  }

  redirect(noticePath(returnTo, "telegram-connection-error"));
}

export async function triggerOutboundCallAction(formData: FormData) {
  let agentId = textValue(formData, "agent_id");
  const toNumber = textValue(formData, "to_number");
  const returnTo = textValue(formData, "return_to") || "/dashboard";

  if (!toNumber) {
    redirect(noticePath(returnTo, "call-invalid"));
  }

  if (!agentId) {
    const { fetchCoreApi } = await import("../lib/core-api");
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const agentsResult = await fetchCoreApi<any[]>("/api/v1/agents");
    if (agentsResult.state === "live" && agentsResult.data && agentsResult.data.length > 0) {
      agentId = agentsResult.data[0].id;
    } else {
      agentId = "389a4f13-05d3-5860-af9f-69bd9ce2493a";
    }
  }

  const result = await mutateCoreApi<{ call_sid: string; status: string }>("/api/v1/voice/calls/outbound", {
    agent_id: agentId,
    to_number: toNumber,
  });

  if (result.state === "live") {
    redirect(noticePath(returnTo, "call-initiated"));
  }

  redirect(noticePath(returnTo, "call-error"));
}

export async function createApiKeyAction(formData: FormData) {
  const name = textValue(formData, "name");
  const scopesVal = textValue(formData, "scopes") || "read,write";
  const scopes = scopesVal.split(",");

  if (!name) {
    redirect(noticePath("/settings/api-keys", "key-invalid"));
  }

  const result = await mutateCoreApi<{ id: string; key: string; name: string }>(
    "/api/v1/api-keys",
    { name, scopes }
  );

  if (result.state === "live") {
    redirect(`/settings/api-keys?notice=key-created&new_key=${result.data.key}&new_name=${result.data.name}`);
  }

  redirect(noticePath("/settings/api-keys", "key-error"));
}

export async function revokeApiKeyAction(formData: FormData) {
  const keyId = textValue(formData, "key_id");

  if (!keyId) {
    redirect(noticePath("/settings/api-keys", "key-revoke-invalid"));
  }

  const result = await deleteCoreApiNoContent(`/api/v1/api-keys/${keyId}`);

  if (result.state === "live") {
    redirect(noticePath("/settings/api-keys", "key-revoked"));
  }

  redirect(noticePath("/settings/api-keys", "key-revoke-error"));
}

export async function inviteTeamMemberAction(formData: FormData) {
  const email = textValue(formData, "email");
  const name = textValue(formData, "name");
  const role = textValue(formData, "role") || "viewer";

  if (!email || !name) {
    redirect(noticePath("/settings/team", "invite-invalid"));
  }

  const result = await mutateCoreApi<{ message: string }>("/api/v1/team/invite", {
    email,
    name,
    role,
  });

  if (result.state === "live") {
    redirect(`/settings/team?notice=member-invited&invite_msg=${encodeURIComponent(result.data.message)}`);
  }

  redirect(noticePath("/settings/team", "invite-error"));
}

export async function updateTeamMemberRoleAction(formData: FormData) {
  const memberId = textValue(formData, "member_id");
  const role = textValue(formData, "role");

  if (!memberId || !role) {
    redirect(noticePath("/settings/team", "role-invalid"));
  }

  const result = await patchCoreApi(`/api/v1/team/members/${memberId}/role`, {
    role,
  });

  if (result.state === "live") {
    redirect(noticePath("/settings/team", "role-updated"));
  }

  redirect(noticePath("/settings/team", "role-error"));
}

export async function removeTeamMemberAction(formData: FormData) {
  const memberId = textValue(formData, "member_id");

  if (!memberId) {
    redirect(noticePath("/settings/team", "remove-invalid"));
  }

  const result = await deleteCoreApiNoContent(`/api/v1/team/members/${memberId}`);

  if (result.state === "live") {
    redirect(noticePath("/settings/team", "member-removed"));
  }

  redirect(noticePath("/settings/team", "remove-error"));
}


export async function getAgentPathwayAction(agentId: string) {
  const { fetchCoreApi } = await import("../lib/core-api");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const result = await fetchCoreApi<{ nodes: any[]; edges: any[] }>(`/api/v1/agents/${agentId}/pathway`);
  if (result.state === "live") {
    return { success: true, data: result.data };
  }
  return { success: false, error: result.message || "Failed to load pathway" };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function saveAgentPathwayAction(agentId: string, nodes: any[], edges: any[]) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const result = await mutateCoreApi<{ nodes: any[]; edges: any[] }>(`/api/v1/agents/${agentId}/pathway`, {
    nodes,
    edges,
  });
  if (result.state === "live") {
    return { success: true, data: result.data };
  }
  return { success: false, error: result.message || "Failed to save pathway" };
}

export async function sendVoicePreviewMessageAction(agentId: string, message: string, sessionId: string) {
  const result = await mutateCoreApi<{ response_text: string; conversation_id: string }>(
    `/api/v1/voice/sessions/${encodeURIComponent(sessionId)}/preview-turn`,
    {
      agent_id: agentId,
      text: message,
    }
  );
  if (result.state === "live") {
    return { success: true, response_text: result.data.response_text || "" };
  }
  return { success: false, error: result.message || "Failed to process turn" };
}
