import Link from "next/link";
import { ArrowLeft, Save, MessageSquare, PhoneCall, CreditCard, HelpCircle } from "lucide-react";
import { DashboardShell } from "../../components/DashboardShell";
import { updateTenantSettingsAction } from "../../actions";
import { fetchCoreApi, getCoreTenantId } from "../../../lib/core-api";

export const metadata = {
  title: "Каналы связи - CallForce",
};

export default async function ChannelsPage({
  searchParams,
}: {
  searchParams: Promise<{ notice?: string }>;
}) {
  const [{ notice }, tenantId] = await Promise.all([
    searchParams,
    getCoreTenantId(),
  ]);

  // Fetch current settings
  const settingsResult = await fetchCoreApi<Record<string, string>>(`/api/v1/tenants/${tenantId}/settings`);
  const settings = settingsResult.state === "live" ? settingsResult.data : {};

  const isUpdated = notice === "settings-updated";
  const isError = notice === "settings-error";

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
      <div className="max-w-4xl space-y-6">
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

        <form action={updateTenantSettingsAction} className="space-y-8">

          {/* Telegram Block */}
          <section className="bg-zinc-900/40 border border-white/5 rounded-xl p-6 space-y-4">
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
          <section className="bg-zinc-900/40 border border-white/5 rounded-xl p-6 space-y-4">
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
          <section className="bg-zinc-900/40 border border-white/5 rounded-xl p-6 space-y-4">
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
