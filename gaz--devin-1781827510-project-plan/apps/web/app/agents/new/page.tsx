import Link from "next/link";
import { createAgentAction } from "../../actions";
import { ActionNotice } from "../../components/ActionNotice";
import { DashboardShell } from "../../components/DashboardShell";

type NewAgentPageProps = {
  searchParams?: Promise<{
    notice?: string;
  }>;
};

export default async function NewAgentPage({ searchParams }: NewAgentPageProps) {
  const notice = (await searchParams)?.notice;

  return (
    <DashboardShell
      activePath="/agents"
      eyebrow="Agent Builder"
      title="Создать draft агента"
      description="Создайте draft-агента, затем откройте карточку для тестирования, редактирования и публикации."
      actions={
        <Link
          href="/agents"
          className="flex items-center gap-2 bg-white/5 text-zinc-300 border border-white/10 px-4 py-2 rounded-lg text-sm font-medium hover:bg-white/10 hover:text-white transition-colors"
        >
          Назад к агентам
        </Link>
      }
    >
      <ActionNotice notice={notice} />
      <section className="glass-panel premium-border p-8 max-w-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-primary/10 rounded-full blur-3xl -mr-32 -mt-32 pointer-events-none"></div>
        <form action={createAgentAction} className="space-y-6">
          <div className="grid sm:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-300">Название</label>
              <input
                className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-4 py-2.5 text-sm text-foreground placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner"
                name="name"
                placeholder="Например, Restaurant Support RU"
                required
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-300">Основной канал</label>
              <select
                className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner appearance-none"
                defaultValue="telegram"
                name="channel"
              >
                <option value="telegram">Telegram</option>
                <option value="web_widget">Web widget</option>
                <option value="sip">SIP voice</option>
              </select>
            </div>

            <div className="sm:col-span-2 space-y-2">
              <label className="text-sm font-medium text-zinc-300">Цель агента</label>
              <textarea
                className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-4 py-2.5 text-sm text-foreground placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner resize-y"
                name="goal"
                placeholder="Например: отвечать на FAQ, помогать с доставкой и передавать сложные кейсы оператору."
                rows={3}
              />
            </div>

            <div className="sm:col-span-2 space-y-4 border-t border-white/5 pt-4">
              <h3 className="text-sm font-semibold text-white">Agent profile</h3>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-2">
                  <label className="text-xs font-medium text-zinc-400">Role</label>
                  <select
                    className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner"
                    defaultValue="customer_support"
                    name="agent_role"
                  >
                    <option value="customer_support">Support</option>
                    <option value="sales_consultant">Sales consultant</option>
                    <option value="receptionist">Receptionist</option>
                    <option value="qa_supervisor">QA supervisor</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-medium text-zinc-400">Tone</label>
                  <select
                    className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner"
                    defaultValue="professional"
                    name="agent_tone"
                  >
                    <option value="professional">Professional</option>
                    <option value="friendly">Friendly</option>
                    <option value="concise">Concise</option>
                    <option value="premium">Premium</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-medium text-zinc-400">Language</label>
                  <select
                    className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner"
                    defaultValue="ru"
                    name="agent_language"
                  >
                    <option value="ru">RU</option>
                    <option value="en">EN</option>
                    <option value="mixed_ru_en">RU + EN</option>
                  </select>
                </div>
              </div>

              <label className="block space-y-2">
                <span className="text-xs font-medium text-zinc-400">Business profile</span>
                <textarea
                  className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-4 py-2.5 text-sm text-foreground placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner resize-y"
                  name="business_profile"
                  placeholder="Company, offer, audience, geography, pricing rules, service limits."
                  rows={4}
                />
              </label>

              <div className="grid gap-4 sm:grid-cols-3">
                <label className="space-y-2">
                  <span className="text-xs font-medium text-zinc-400">Business hours</span>
                  <textarea
                    className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner resize-y"
                    name="business_hours"
                    placeholder="Mon-Fri 09:00-18:00, Samara time."
                    rows={3}
                  />
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-medium text-zinc-400">Escalation rules</span>
                  <textarea
                    className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner resize-y"
                    name="escalation_rules"
                    placeholder="Escalate refunds, legal questions, VIP clients."
                    rows={3}
                  />
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-medium text-zinc-400">Sales rules</span>
                  <textarea
                    className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner resize-y"
                    name="sales_rules"
                    placeholder="Qualify need, budget, timing; never promise discounts."
                    rows={3}
                  />
                </label>
              </div>

              <label className="block space-y-2">
                <span className="text-xs font-medium text-zinc-400">Forbidden topics</span>
                <textarea
                  className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-4 py-2.5 text-sm text-foreground placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner resize-y"
                  name="forbidden_topics"
                  placeholder="One topic per line."
                  rows={3}
                />
              </label>
            </div>

            <div className="sm:col-span-2 space-y-3 border-t border-white/5 pt-4">
              <input name="enabled_tools" type="hidden" value="escalate_to_human" />
              <h3 className="text-sm font-semibold text-white">Enabled tools</h3>
              <div className="grid gap-3 sm:grid-cols-2">
                {[
                  ["add_to_cart", "Add order item"],
                  ["remove_from_cart", "Remove order item"],
                  ["checkout_cart", "Collect checkout details"],
                  ["confirm_order", "Confirm order"],
                ].map(([value, label]) => (
                  <label
                    key={value}
                    className="flex min-h-11 items-center gap-3 rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-zinc-300"
                  >
                    <input
                      className="h-4 w-4 rounded border-white/20 bg-black text-primary focus:ring-primary/40"
                      name="enabled_tools"
                      type="checkbox"
                      value={value}
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>

            <div className="sm:col-span-2 space-y-4 border-t border-white/5 pt-4">
              <h3 className="text-sm font-semibold text-white">Настройки голоса (для SIP и голосового стриминга)</h3>
              <div className="grid sm:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <label className="text-xs font-medium text-zinc-400">ID Голоса</label>
                  <select
                    className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner"
                    defaultValue="alloy"
                    name="voice_id"
                  >
                    <option value="alloy">Alloy (Balanced)</option>
                    <option value="echo">Echo (Warm)</option>
                    <option value="fable">Fable (Narrator)</option>
                    <option value="onyx">Onyx (Deep)</option>
                    <option value="nova">Nova (Bright)</option>
                    <option value="shimmer">Shimmer (Professional)</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-medium text-zinc-400">Язык</label>
                  <select
                    className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner"
                    defaultValue="ru"
                    name="voice_language"
                  >
                    <option value="ru">Русский (RU)</option>
                    <option value="en">English (EN)</option>
                    <option value="es">Español (ES)</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-medium text-zinc-400">Скорость речи</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.5"
                    max="2.0"
                    className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner"
                    name="voice_speed"
                    defaultValue="1.0"
                    required
                  />
                </div>
              </div>
            </div>

            <div className="sm:col-span-2 space-y-4 border-t border-white/5 pt-4">
              <h3 className="text-sm font-semibold text-white">Параметры LLM</h3>
              <div className="grid sm:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <label className="text-xs font-medium text-zinc-400">Модель LLM</label>
                  <select
                    className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner"
                    defaultValue="gpt-4o-mini"
                    name="model_name"
                  >
                    <option value="gpt-4o-mini">gpt-4o-mini (Fast)</option>
                    <option value="gpt-4o">gpt-4o (Smart)</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-medium text-zinc-400">Температура</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.0"
                    max="2.0"
                    className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner"
                    name="temperature"
                    defaultValue="0.3"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-medium text-zinc-400">Max tokens</label>
                  <input
                    type="number"
                    min="100"
                    max="4000"
                    className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner"
                    name="max_tokens"
                    defaultValue="1024"
                    required
                  />
                </div>
              </div>
            </div>

            <div className="sm:col-span-2 space-y-2 border-t border-white/5 pt-4">
              <label className="text-sm font-medium text-zinc-300">System prompt</label>
              <textarea
                className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-4 py-2.5 text-sm text-foreground placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner resize-y"
                name="prompt"
                placeholder="Ты AI-оператор ресторана. Отвечай коротко, используй только подтвержденные источники, не изменяй заказ без явного подтверждения клиента."
                required
                rows={5}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-300">LLM policy</label>
              <select
                className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner appearance-none font-medium"
                defaultValue="safe-rag"
                name="policy"
              >
                <option value="safe-rag">Safe RAG with no-answer policy</option>
                <option value="handoff-first">Handoff-first</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-300">Knowledge source</label>
              <select
                className="w-full bg-black/40 backdrop-blur-sm border border-border rounded-lg px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-inner appearance-none font-medium"
                defaultValue="ks-menu-faq"
                name="knowledgeSourceId"
              >
                <option value="ks-menu-faq">Меню и FAQ доставки.pdf</option>
                <option value="ks-website">Website FAQ</option>
              </select>
            </div>
          </div>

          <div className="p-4 rounded-lg bg-primary/10 border border-primary/20 text-primary text-sm font-medium">
            Сохранение идет через live Core API и появится в списке агентов tenant-а.
          </div>

          <div className="flex flex-col gap-3 pt-4 border-t border-white/5 sm:flex-row sm:items-center sm:gap-4">
            <button
              className="bg-white text-black font-medium px-6 py-2.5 rounded-lg hover:bg-zinc-200 transition-colors"
              type="submit"
            >
              Сохранить draft
            </button>
            <Link
              href="/agents"
              className="px-6 py-2.5 rounded-lg text-center text-sm font-medium text-zinc-300 border border-white/10 hover:bg-white/5 hover:text-white transition-colors"
            >
              Отмена
            </Link>
          </div>
        </form>
      </section>
    </DashboardShell>
  );
}
