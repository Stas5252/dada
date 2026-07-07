import Link from "next/link";
import { AlertTriangle, ArrowLeft, Bot, CheckCircle2, CreditCard, ExternalLink, FlaskConical, HelpCircle, MessageCircle, MessageSquare, PhoneCall, Save, ShieldCheck, Utensils } from "lucide-react";
import { DashboardShell } from "../../components/DashboardShell";
import { updateChannelPoliciesAction, updateTenantSettingsAction } from "../../actions";
import {
  fetchCoreApi,
  getCoreTenantId,
  type CoreChannelCompliancePolicySettings,
  type CoreChannelPoliciesSettings,
  type CoreChannelWebhookDiagnosticItem,
  type CoreChannelWebhookDiagnosticsResponse,
  type CoreIntegrationReadinessItem,
  type CoreIntegrationReadinessResponse,
} from "../../../lib/core-api";

export const metadata = {
  title: "Каналы связи - CallForce",
};

const defaultChannelPolicy: CoreChannelCompliancePolicySettings = {
  mode: "autopilot",
  outbound_enabled: true,
  ai_disclosure_required: false,
  require_opt_out_notice: false,
  require_contact_consent_for_outbound: false,
  max_auto_replies_per_conversation: 100,
};

const defaultChannelPolicies: CoreChannelPoliciesSettings = {
  default_policy: defaultChannelPolicy,
  web_widget: defaultChannelPolicy,
  telegram: defaultChannelPolicy,
  vk: defaultChannelPolicy,
  whatsapp: defaultChannelPolicy,
  voice: defaultChannelPolicy,
};

const defaultIntegrationReadiness: CoreIntegrationReadinessResponse = {
  status: "action_required",
  checked_at: "",
  items: [],
};

const defaultWebhookDiagnostics: CoreChannelWebhookDiagnosticsResponse = {
  checked_at: "",
  public_base_url: "",
  public_url_status: "missing",
  items: [],
};

const channelPolicyRows: Array<{
  key: keyof CoreChannelPoliciesSettings;
  label: string;
  description: string;
}> = [
  { key: "web_widget", label: "Web widget", description: "Ответы в виджете сайта." },
  { key: "telegram", label: "Telegram", description: "Сообщения Telegram Bot API." },
  { key: "vk", label: "VK", description: "Сообщения сообщества VK." },
  { key: "whatsapp", label: "WhatsApp", description: "WhatsApp Business API." },
  { key: "voice", label: "Voice", description: "Исходящие звонки и SMS." },
];

function channelPolicyWithDefaults(
  policy?: Partial<CoreChannelCompliancePolicySettings>,
): CoreChannelCompliancePolicySettings {
  return {
    ...defaultChannelPolicy,
    ...policy,
  };
}

function readinessStatusLabel(status: CoreIntegrationReadinessItem["status"]) {
  if (status === "configured") {
    return "Ready";
  }
  if (status === "needs_setup") {
    return "Setup needed";
  }
  return "Local stub";
}

function readinessStatusClass(status: CoreIntegrationReadinessItem["status"]) {
  if (status === "configured") {
    return "border-emerald-500/25 bg-emerald-500/10 text-emerald-300";
  }
  if (status === "needs_setup") {
    return "border-amber-500/25 bg-amber-500/10 text-amber-200";
  }
  return "border-sky-500/25 bg-sky-500/10 text-sky-200";
}

function readinessIcon(status: CoreIntegrationReadinessItem["status"]) {
  if (status === "configured") {
    return <CheckCircle2 className="h-4 w-4" />;
  }
  if (status === "needs_setup") {
    return <AlertTriangle className="h-4 w-4" />;
  }
  return <FlaskConical className="h-4 w-4" />;
}

function webhookStatusLabel(status: CoreChannelWebhookDiagnosticItem["status"]) {
  if (status === "ready") {
    return "Ready";
  }
  if (status === "warning") {
    return "Warning";
  }
  return "Setup needed";
}

function webhookStatusClass(status: CoreChannelWebhookDiagnosticItem["status"]) {
  if (status === "ready") {
    return "border-emerald-500/25 bg-emerald-500/10 text-emerald-300";
  }
  if (status === "warning") {
    return "border-sky-500/25 bg-sky-500/10 text-sky-200";
  }
  return "border-amber-500/25 bg-amber-500/10 text-amber-200";
}

function ReadinessChecklist({
  items,
}: {
  items: CoreIntegrationReadinessItem[];
}) {
  return (
    <section className="space-y-4 rounded-xl border border-white/5 bg-zinc-900/40 p-6">
      <div className="flex flex-col gap-3 border-b border-white/5 pb-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <ShieldCheck className="mt-1 h-6 w-6 text-emerald-400" />
          <div>
            <h2 className="text-lg font-semibold text-white">Production launch readiness</h2>
            <p className="mt-1 text-xs leading-5 text-zinc-400">
              Tenant-level diagnostics for live channels, AI, voice, payments and order integrations.
            </p>
          </div>
        </div>
        <div className="text-xs text-zinc-500">{items.length} checks</div>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => (
          <div
            key={item.key}
            className="rounded-lg border border-white/5 bg-black/30 p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-white">{item.label}</div>
                <div className="mt-1 text-xs text-zinc-500">{item.category}</div>
              </div>
              <span
                className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-1 text-[11px] font-medium ${readinessStatusClass(item.status)}`}
              >
                {readinessIcon(item.status)}
                {readinessStatusLabel(item.status)}
              </span>
            </div>
            <p className="mt-3 text-xs leading-5 text-zinc-400">{item.summary}</p>
            {item.missing_settings.length > 0 && (
              <div className="mt-3 text-xs text-zinc-500">
                Missing: {item.missing_settings.slice(0, 3).join(", ")}
                {item.missing_settings.length > 3 ? "..." : ""}
              </div>
            )}
            {item.setup_url && (
              <Link
                href={item.setup_url}
                className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-emerald-300 hover:text-emerald-200"
              >
                Open setup
                <ExternalLink className="h-3 w-3" />
              </Link>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function WebhookDiagnostics({
  diagnostics,
}: {
  diagnostics: CoreChannelWebhookDiagnosticsResponse;
}) {
  return (
    <section className="space-y-4 rounded-xl border border-white/5 bg-zinc-900/40 p-6">
      <div className="flex flex-col gap-3 border-b border-white/5 pb-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <MessageSquare className="mt-1 h-6 w-6 text-sky-300" />
          <div>
            <h2 className="text-lg font-semibold text-white">Webhook diagnostics</h2>
            <p className="mt-1 text-xs leading-5 text-zinc-400">
              Provider callback URLs, HTTPS readiness and missing channel settings.
            </p>
          </div>
        </div>
        <span
          className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-1 text-[11px] font-medium ${
            diagnostics.public_url_status === "https_ready"
              ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-300"
              : "border-amber-500/25 bg-amber-500/10 text-amber-200"
          }`}
        >
          {diagnostics.public_url_status === "https_ready" ? "Public HTTPS" : "Local URL"}
        </span>
      </div>
      <div className="grid gap-3 lg:grid-cols-3">
        {diagnostics.items.map((item) => (
          <div key={item.key} className="rounded-lg border border-white/5 bg-black/30 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-white">{item.label}</div>
                <div className="mt-1 text-xs text-zinc-500">{item.provider}</div>
              </div>
              <span
                className={`inline-flex shrink-0 rounded-full border px-2 py-1 text-[11px] font-medium ${webhookStatusClass(item.status)}`}
              >
                {webhookStatusLabel(item.status)}
              </span>
            </div>
            <p className="mt-3 text-xs leading-5 text-zinc-400">{item.summary}</p>
            {item.inbound_webhook_url && (
              <div className="mt-3 rounded-md border border-white/5 bg-zinc-950 px-3 py-2 font-mono text-[11px] leading-5 text-zinc-300 break-all">
                {item.inbound_webhook_url}
              </div>
            )}
            {item.missing_settings.length > 0 && (
              <div className="mt-3 text-xs text-zinc-500">
                Missing: {item.missing_settings.slice(0, 4).join(", ")}
                {item.missing_settings.length > 4 ? "..." : ""}
              </div>
            )}
            {item.warnings.length > 0 && (
              <div className="mt-3 text-xs leading-5 text-amber-200">
                {item.warnings[0]}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function ChannelPolicyRow({
  channelKey,
  description,
  label,
  policy,
}: {
  channelKey: keyof CoreChannelPoliciesSettings;
  description: string;
  label: string;
  policy: CoreChannelCompliancePolicySettings;
}) {
  return (
    <div className="grid gap-3 border-t border-white/5 py-4 lg:grid-cols-[minmax(170px,1fr)_160px_96px_116px_116px_120px_120px] lg:items-center">
      <div>
        <div className="text-sm font-semibold text-white">{label}</div>
        <div className="mt-1 text-xs text-zinc-500">{description}</div>
      </div>
      <label className="space-y-1">
        <span className="text-xs font-medium text-zinc-500">Режим</span>
        <select
          name={`${channelKey}_mode`}
          defaultValue={policy.mode}
          className="w-full rounded-lg border border-white/10 bg-black px-3 py-2 text-sm text-white outline-none transition-colors focus:border-emerald-500"
        >
          <option value="autopilot">Autopilot</option>
          <option value="draft_only">Draft only</option>
          <option value="human_approval">Human approval</option>
        </select>
      </label>
      <label className="flex items-center gap-2 text-sm text-zinc-300 lg:pt-5">
        <input
          type="checkbox"
          name={`${channelKey}_outbound_enabled`}
          defaultChecked={policy.outbound_enabled}
          className="h-4 w-4 rounded border-white/20 bg-black text-emerald-500 focus:ring-emerald-500"
        />
        Outbound
      </label>
      <label className="flex items-center gap-2 text-sm text-zinc-300 lg:pt-5">
        <input
          type="checkbox"
          name={`${channelKey}_ai_disclosure_required`}
          defaultChecked={policy.ai_disclosure_required}
          className="h-4 w-4 rounded border-white/20 bg-black text-emerald-500 focus:ring-emerald-500"
        />
        AI disclosure
      </label>
      <label className="space-y-1">
        <span className="text-xs font-medium text-zinc-500">Auto replies</span>
        <input
          type="number"
          name={`${channelKey}_max_auto_replies_per_conversation`}
          min={0}
          max={1000}
          defaultValue={policy.max_auto_replies_per_conversation}
          className="w-full rounded-lg border border-white/10 bg-black px-3 py-2 text-sm text-white outline-none transition-colors focus:border-emerald-500"
        />
      </label>
      <label className="flex items-center gap-2 text-sm text-zinc-300 lg:pt-5">
        <input
          type="checkbox"
          name={`${channelKey}_require_opt_out_notice`}
          defaultChecked={policy.require_opt_out_notice}
          className="h-4 w-4 rounded border-white/20 bg-black text-emerald-500 focus:ring-emerald-500"
        />
        Opt-out notice
      </label>
      <label className="flex items-center gap-2 text-sm text-zinc-300 lg:pt-5">
        <input
          type="checkbox"
          name={`${channelKey}_require_contact_consent_for_outbound`}
          defaultChecked={policy.require_contact_consent_for_outbound}
          className="h-4 w-4 rounded border-white/20 bg-black text-emerald-500 focus:ring-emerald-500"
        />
        Consent required
      </label>
      <input
        type="hidden"
        name={`${channelKey}_require_opt_out_notice`}
        value=""
      />
      <input
        type="hidden"
        name={`${channelKey}_require_contact_consent_for_outbound`}
        value=""
      />
    </div>
  );
}

export default async function ChannelsPage({
  searchParams,
}: {
  searchParams: Promise<{ notice?: string }>;
}) {
  const [{ notice }, tenantId] = await Promise.all([
    searchParams,
    getCoreTenantId(),
  ]);

  const [
    settingsResult,
    channelPoliciesResult,
    integrationReadinessResult,
    webhookDiagnosticsResult,
  ] = await Promise.all([
    fetchCoreApi<Record<string, string>>(`/api/v1/tenants/${tenantId}/settings`),
    fetchCoreApi<CoreChannelPoliciesSettings>(`/api/v1/tenants/${tenantId}/settings/channel-policies`),
    fetchCoreApi<CoreIntegrationReadinessResponse>(
      `/api/v1/tenants/${tenantId}/settings/integration-readiness`,
    ),
    fetchCoreApi<CoreChannelWebhookDiagnosticsResponse>(
      `/api/v1/tenants/${tenantId}/settings/channel-webhooks`,
    ),
  ]);
  const settings = settingsResult.state === "live" ? settingsResult.data : {};
  const channelPolicies =
    channelPoliciesResult.state === "live" ? channelPoliciesResult.data : defaultChannelPolicies;
  const integrationReadiness =
    integrationReadinessResult.state === "live"
      ? integrationReadinessResult.data
      : defaultIntegrationReadiness;
  const webhookDiagnostics =
    webhookDiagnosticsResult.state === "live"
      ? webhookDiagnosticsResult.data
      : defaultWebhookDiagnostics;

  const isUpdated = notice === "settings-updated";
  const isError = notice === "settings-error";
  const isChannelPoliciesUpdated = notice === "channel-policies-updated";
  const isChannelPoliciesError = notice === "channel-policies-error";

  return (
    <DashboardShell
      activePath="/settings/channels"
      eyebrow="Каналы связи"
      title="Интеграция каналов и платежей"
      description="Настройка ключей доступа для работы Telegram, телефонии Twilio и платежной системы ЮKassa."
      actions={
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm font-medium text-zinc-300 transition-colors hover:bg-white/10 hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          В панель
        </Link>
      }
    >
      <div className="max-w-5xl space-y-6">
        {isUpdated && (
          <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
            <strong className="font-semibold text-white">Успех:</strong> Настройки каналов успешно обновлены и сохранены.
          </div>
        )}
        {isError && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            <strong className="font-semibold text-white">Ошибка:</strong> Не удалось обновить настройки. Пожалуйста, проверьте вводимые данные.
          </div>
        )}
        {isChannelPoliciesUpdated && (
          <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
            <strong className="font-semibold text-white">Успех:</strong> Channel policies сохранены.
          </div>
        )}
        {isChannelPoliciesError && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            <strong className="font-semibold text-white">Ошибка:</strong> Не удалось сохранить channel policies.
          </div>
        )}
        {channelPoliciesResult.state !== "live" && (
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
            <strong className="font-semibold text-white">Channel policies:</strong> {channelPoliciesResult.message}
          </div>
        )}
        {integrationReadinessResult.state !== "live" && (
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
            <strong className="font-semibold text-white">Integration readiness:</strong> {integrationReadinessResult.message}
          </div>
        )}
        {webhookDiagnosticsResult.state !== "live" && (
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
            <strong className="font-semibold text-white">Webhook diagnostics:</strong> {webhookDiagnosticsResult.message}
          </div>
        )}

        <ReadinessChecklist items={integrationReadiness.items} />
        <WebhookDiagnostics diagnostics={webhookDiagnostics} />

        <form action={updateChannelPoliciesAction}>
          <section className="space-y-4 rounded-xl border border-white/5 bg-zinc-900/40 p-6">
            <div className="flex flex-col gap-3 border-b border-white/5 pb-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex items-start gap-3">
                <ShieldCheck className="mt-1 h-6 w-6 text-emerald-400" />
                <div>
                  <h2 className="text-lg font-semibold text-white">Режимы каналов</h2>
                  <p className="mt-1 text-xs leading-5 text-zinc-400">
                    Autopilot отправляет ответ клиенту сразу. Draft only сохраняет черновик. Human approval требует ручной отправки оператором.
                  </p>
                </div>
              </div>
              <button
                type="submit"
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-4 py-2.5 text-sm font-medium text-black transition-colors hover:bg-zinc-200"
              >
                <Bot className="h-4 w-4" />
                Сохранить режимы
              </button>
            </div>
            <input type="hidden" name="default_policy_mode" value={channelPolicies.default_policy.mode} />
            <input
              type="hidden"
              name="default_policy_max_auto_replies_per_conversation"
              value={channelPolicies.default_policy.max_auto_replies_per_conversation}
            />
            {channelPolicies.default_policy.outbound_enabled && (
              <input type="hidden" name="default_policy_outbound_enabled" value="on" />
            )}
            {channelPolicies.default_policy.ai_disclosure_required && (
              <input type="hidden" name="default_policy_ai_disclosure_required" value="on" />
            )}
            {channelPolicies.default_policy.require_opt_out_notice && (
              <input type="hidden" name="default_policy_require_opt_out_notice" value="on" />
            )}
            {channelPolicies.default_policy.require_contact_consent_for_outbound && (
              <input
                type="hidden"
                name="default_policy_require_contact_consent_for_outbound"
                value="on"
              />
            )}
            <div>
              {channelPolicyRows.map((row) => (
                <ChannelPolicyRow
                  key={row.key}
                  channelKey={row.key}
                  label={row.label}
                  description={row.description}
                  policy={channelPolicyWithDefaults(channelPolicies[row.key])}
                />
              ))}
            </div>
          </section>
        </form>

        <form action={updateTenantSettingsAction} className="space-y-8">

          {/* OpenAI Integration Block */}
          <section id="openai" className="bg-zinc-900/40 border border-white/5 rounded-xl p-6 space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-3">
              <MessageCircle className="w-6 h-6 text-purple-400" />
              <div>
                <h2 className="text-lg font-semibold text-white">Модели ИИ (OpenAI)</h2>
                <p className="text-xs text-zinc-400">Собственный ключ для генерации ответов и работы агентов.</p>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-300 block">OpenAI API Key (BYOK)</label>
              <input
                type="password"
                name="openai_api_key"
                defaultValue={settings.openai_api_key || ""}
                placeholder="sk-..."
                className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-purple-500"
              />
              <div className="mt-2 flex items-start gap-2 text-xs text-zinc-400 bg-white/5 p-3 rounded-lg border border-white/5">
                <HelpCircle className="w-4 h-4 text-zinc-400 flex-shrink-0 mt-0.5" />
                <p>
                  Как настроить: Перейдите на <b>platform.openai.com</b>, создайте новый API-ключ в разделе API Keys и вставьте его сюда. Этот ключ будет использоваться вашими ИИ-агентами (если не указано, система будет использовать мок-генерацию).
                </p>
              </div>
            </div>
          </section>

          {/* Telegram Block */}
          <section id="telegram" className="bg-zinc-900/40 border border-white/5 rounded-xl p-6 space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-3">
              <MessageSquare className="w-6 h-6 text-sky-400" />
              <div>
                <h2 className="text-lg font-semibold text-white">Интеграция Telegram</h2>
                <p className="text-xs text-zinc-400">Подключение вашего ИИ-агента к Telegram-боту.</p>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-300 block">Telegram Bot Token</label>
              <input
                type="text"
                name="telegram_bot_token"
                defaultValue={settings.telegram_bot_token || ""}
                placeholder="123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
                className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-sky-500"
              />
              <div className="mt-2 flex items-start gap-2 text-xs text-zinc-400 bg-white/5 p-3 rounded-lg border border-white/5">
                <HelpCircle className="w-4 h-4 text-zinc-400 flex-shrink-0 mt-0.5" />
                <p>
                  Как настроить: Напишите <b>@BotFather</b> в Telegram, создайте нового бота с помощью команды <code>/newbot</code>, скопируйте полученный Token и вставьте сюда. Бот будет автоматически отвечать клиентам с учетом базы знаний.
                </p>
              </div>
            </div>
          </section>

          {/* Twilio Telephony Block */}
          <section id="twilio" className="bg-zinc-900/40 border border-white/5 rounded-xl p-6 space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-3">
              <PhoneCall className="w-6 h-6 text-emerald-400" />
              <div>
                <h2 className="text-lg font-semibold text-white">Телефония Twilio (Голос и SMS)</h2>
                <p className="text-xs text-zinc-400">Входящие и исходящие телефонные звонки для ваших агентов.</p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-300 block">Twilio Account SID</label>
                <input
                  type="text"
                  name="twilio_account_sid"
                  defaultValue={settings.twilio_account_sid || ""}
                  placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                  className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-emerald-500"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-300 block">Twilio Auth Token</label>
                <input
                  type="password"
                  name="twilio_auth_token"
                  defaultValue={settings.twilio_auth_token || ""}
                  placeholder="••••••••••••••••••••••••••••••••"
                  className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-emerald-500"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-300 block">Номер телефона Twilio (в формате +15005550006)</label>
              <input
                type="text"
                name="twilio_phone_number"
                defaultValue={settings.twilio_phone_number || ""}
                placeholder="+15005550006"
                className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-emerald-500"
              />
              <div className="mt-2 flex items-start gap-2 text-xs text-zinc-400 bg-white/5 p-3 rounded-lg border border-white/5">
                <HelpCircle className="w-4 h-4 text-zinc-400 flex-shrink-0 mt-0.5" />
                <p>
                  Как настроить: Зарегистрируйте аккаунт на <b>Twilio.com</b>, получите тестовый или постоянный номер, скопируйте Account SID и Auth Token из панели управления. Для входящих звонков укажите в настройках номера вебхук: <code>http://&lt;ваш-домен&gt;/api/v1/voice/webhooks/twilio/voice/&lt;agent_id&gt;</code>.
                </p>
              </div>
            </div>
          </section>

          {/* YooKassa Payment Block */}
          <section id="yookassa" className="bg-zinc-900/40 border border-white/5 rounded-xl p-6 space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-3">
              <CreditCard className="w-6 h-6 text-purple-400" />
              <div>
                <h2 className="text-lg font-semibold text-white">Платежная система ЮKassa</h2>
                <p className="text-xs text-zinc-400">Прием оплаты за заказы прямо во время диалогов.</p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-300 block">Идентификатор магазина (Shop ID)</label>
                <input
                  type="text"
                  name="yookassa_shop_id"
                  defaultValue={settings.yookassa_shop_id || ""}
                  placeholder="123456"
                  className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-purple-500"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-300 block">Секретный ключ (Secret Key)</label>
                <input
                  type="password"
                  name="yookassa_secret_key"
                  defaultValue={settings.yookassa_secret_key || ""}
                  placeholder="live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                  className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-purple-500"
                />
              </div>
            </div>
          </section>

          {/* iikoCloud Integration Block */}
          <section id="iiko" className="bg-zinc-900/40 border border-white/5 rounded-xl p-6 space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-3">
              <Utensils className="w-6 h-6 text-amber-400" />
              <div>
                <h2 className="text-lg font-semibold text-white">Интеграция с iikoCloud</h2>
                <p className="text-xs text-zinc-400">Синхронизация меню ресторана и автоматическое создание заказов.</p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-300 block">Логин API (apiLogin)</label>
                <input
                  type="text"
                  name="iiko_api_login"
                  defaultValue={settings.iiko_api_login || ""}
                  placeholder="e.g. 5d5a7d6e..."
                  className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-amber-500"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-300 block">ID Организации (Organization ID)</label>
                <input
                  type="text"
                  name="iiko_organization_id"
                  defaultValue={settings.iiko_organization_id || ""}
                  placeholder="e.g. 88bc77c2-..."
                  className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-amber-500"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-300 block">ID Группы Терминалов (Terminal Group ID)</label>
                <input
                  type="text"
                  name="iiko_terminal_group_id"
                  defaultValue={settings.iiko_terminal_group_id || ""}
                  placeholder="e.g. 43a6d71b-..."
                  className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-amber-500"
                />
              </div>
            </div>

            <div className="mt-2 flex items-start gap-2 text-xs text-zinc-400 bg-white/5 p-3 rounded-lg border border-white/5">
              <HelpCircle className="w-4 h-4 text-zinc-400 flex-shrink-0 mt-0.5" />
              <p>
                Как настроить: Введите ваши учетные данные iikoCloud. Вы можете найти API Login, ID организации и ID группы терминалов в личном кабинете iikoWeb/iikoCloud. После сохранения меню ресторана будет периодически синхронизироваться с базой знаний ИИ-агента.
              </p>
            </div>
          </section>

          {/* SIP Telephony Block */}
          <section id="sip" className="bg-zinc-900/40 border border-white/5 rounded-xl p-6 space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-3">
              <PhoneCall className="w-6 h-6 text-orange-400" />
              <div>
                <h2 className="text-lg font-semibold text-white">SIP-телефония (Asterisk)</h2>
                <p className="text-xs text-zinc-400">Прямое подключение SIP-транков (Zadarma, Mango, Novofon и др.).</p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-300 block">SIP Server / Proxy</label>
                <input
                  type="text"
                  name="sip_server"
                  defaultValue={settings.sip_server || ""}
                  placeholder="sip.zadarma.com"
                  className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-orange-500"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-300 block">Provider Name</label>
                <input
                  type="text"
                  name="sip_provider"
                  defaultValue={settings.sip_provider || ""}
                  placeholder="zadarma"
                  className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-orange-500"
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-300 block">SIP Login</label>
                <input
                  type="text"
                  name="sip_login"
                  defaultValue={settings.sip_login || ""}
                  placeholder="123456"
                  className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-orange-500"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-300 block">SIP Password</label>
                <input
                  type="password"
                  name="sip_password"
                  defaultValue={settings.sip_password || ""}
                  placeholder="••••••••"
                  className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-orange-500"
                />
              </div>
            </div>

            <div className="mt-2 flex items-start gap-2 text-xs text-zinc-400 bg-white/5 p-3 rounded-lg border border-white/5">
              <HelpCircle className="w-4 h-4 text-zinc-400 flex-shrink-0 mt-0.5" />
              <p>
                Как настроить: Введите данные для авторизации SIP-транка (предоставляются вашим провайдером). Платформа CallForce поднимет транк и будет обрабатывать входящие звонки напрямую через Asterisk ARI.
              </p>
            </div>
          </section>

          {/* WhatsApp Block */}
          <section id="whatsapp" className="bg-zinc-900/40 border border-white/5 rounded-xl p-6 space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-3">
              <MessageCircle className="w-6 h-6 text-green-500" />
              <div>
                <h2 className="text-lg font-semibold text-white">WhatsApp (Meta Cloud API)</h2>
                <p className="text-xs text-zinc-400">Официальная интеграция с WhatsApp Business.</p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-300 block">Access Token</label>
                <input
                  type="password"
                  name="whatsapp_token"
                  defaultValue={settings.whatsapp_token || ""}
                  placeholder="EAAL..."
                  className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-green-500"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-300 block">Phone Number ID</label>
                <input
                  type="text"
                  name="whatsapp_phone_number_id"
                  defaultValue={settings.whatsapp_phone_number_id || ""}
                  placeholder="123456789012345"
                  className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-green-500"
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-300 block">Verify Token (для Webhook)</label>
                <input
                  type="text"
                  name="whatsapp_verify_token"
                  defaultValue={settings.whatsapp_verify_token || ""}
                  placeholder="my_secure_token"
                  className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-green-500"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-300 block">App Secret</label>
                <input
                  type="password"
                  name="whatsapp_app_secret"
                  defaultValue={settings.whatsapp_app_secret || ""}
                  placeholder="Meta app secret"
                  className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-green-500"
                />
              </div>
            </div>
          </section>

          {/* VK Block */}
          <section id="vk" className="bg-zinc-900/40 border border-white/5 rounded-xl p-6 space-y-4">
            <div className="flex items-center gap-3 border-b border-white/5 pb-3">
              <MessageCircle className="w-6 h-6 text-blue-500" />
              <div>
                <h2 className="text-lg font-semibold text-white">ВКонтакте (VK Communities)</h2>
                <p className="text-xs text-zinc-400">Интеграция с сообщениями сообщества ВКонтакте.</p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-300 block">Ключ доступа (Access Token)</label>
                <input
                  type="password"
                  name="vk_group_token"
                  defaultValue={settings.vk_group_token || ""}
                  placeholder="vk1.a.xxxxxxxxxxxxxxxxxxx..."
                  className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-blue-500"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-300 block">Строка подтверждения (Confirmation Code)</label>
                <input
                  type="text"
                  name="vk_confirmation_code"
                  defaultValue={settings.vk_confirmation_code || ""}
                  placeholder="a1b2c3d4"
                  className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-blue-500"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-300 block">Secret Key</label>
                <input
                  type="password"
                  name="vk_secret_key"
                  defaultValue={settings.vk_secret_key || ""}
                  placeholder="Callback secret"
                  className="w-full rounded-lg border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none transition-colors focus:border-blue-500"
                />
              </div>
            </div>
          </section>

          {/* Action Footer */}
          <div className="flex items-center justify-end">
            <button
              type="submit"
              className="flex items-center gap-2 bg-white text-black px-5 py-3 rounded-lg text-sm font-semibold hover:bg-zinc-200 transition-colors cursor-pointer"
            >
              <Save className="w-4 h-4" />
              Сохранить настройки
            </button>
          </div>

        </form>
      </div>
    </DashboardShell>
  );
}
