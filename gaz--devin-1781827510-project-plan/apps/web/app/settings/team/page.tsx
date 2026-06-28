import { DashboardShell } from "../../components/DashboardShell";
import { fetchCoreApi, type CoreUser } from "../../../lib/core-api";
import { Users, UserPlus, Shield, Mail, ShieldCheck, Trash2, AlertTriangle } from "lucide-react";
import { inviteTeamMemberAction, updateTeamMemberRoleAction, removeTeamMemberAction } from "../../actions";
import { SubmitButton } from "../../components/SubmitButton";

type TeamMember = {
  id: string;
  email: string;
  name: string;
  role: string;
  email_verified: boolean;
  mfa_enabled: boolean;
  created_at: string;
};

async function getTeamMembers(): Promise<TeamMember[]> {
  const result = await fetchCoreApi<TeamMember[]>("/api/v1/team/members");
  if (result.state === "live") return result.data;
  return [];
}

const roleLabels: Record<string, { label: string; color: string }> = {
  owner: { label: "Владелец", color: "text-amber-400 bg-amber-400/10" },
  admin: { label: "Админ", color: "text-blue-400 bg-blue-400/10" },
  agent: { label: "Оператор", color: "text-emerald-400 bg-emerald-400/10" },
  viewer: { label: "Наблюдатель", color: "text-zinc-400 bg-zinc-400/10" },
};

function InviteForm() {
  return (
    <div className="p-6 rounded-2xl border border-white/5 bg-zinc-900/50">
      <div className="flex items-center gap-2 mb-4">
        <UserPlus className="w-4 h-4 text-emerald-500" />
        <h3 className="text-sm font-medium text-zinc-400">Пригласить в команду</h3>
      </div>
      <form action={inviteTeamMemberAction} className="space-y-4">
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="invite-name" className="block text-xs font-medium text-zinc-400 mb-1.5">Имя</label>
            <input
              id="invite-name"
              name="name"
              type="text"
              required
              placeholder="Иван Иванов"
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label htmlFor="invite-email" className="block text-xs font-medium text-zinc-400 mb-1.5">Email</label>
            <input
              id="invite-email"
              name="email"
              type="email"
              required
              placeholder="ivan@company.ru"
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
        </div>
        <div className="flex items-end gap-4">
          <div className="flex-1">
            <label htmlFor="invite-role" className="block text-xs font-medium text-zinc-400 mb-1.5">Роль</label>
            <select
              id="invite-role"
              name="role"
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-sans"
            >
              <option value="viewer">Наблюдатель</option>
              <option value="agent">Оператор</option>
              <option value="admin">Админ</option>
            </select>
          </div>
          <SubmitButton
            pendingText="Приглашение..."
            className="px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-500 transition-colors"
          >
            Пригласить
          </SubmitButton>
        </div>
      </form>
    </div>
  );
}

type TeamPageProps = {
  searchParams?: Promise<{
    notice?: string;
    invite_msg?: string;
  }>;
};

export default async function TeamPage({ searchParams }: TeamPageProps) {
  const params = await searchParams;
  const notice = params?.notice;
  const inviteMsg = params?.invite_msg;

  const [displayMembers, userResult] = await Promise.all([
    getTeamMembers(),
    fetchCoreApi<CoreUser>("/api/v1/auth/me"),
  ]);

  const currentUser = userResult.state === "live" ? userResult.data : null;

  return (
    <DashboardShell
      activePath="/settings/team"
      eyebrow="Настройки"
      title="Команда"
      description="Управляйте пользователями и ролями"
    >
      {/* Notices */}
      {notice === "member-invited" && inviteMsg && (
        <div className="mb-6 p-6 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 text-emerald-300 text-sm">
          <h4 className="font-semibold text-white text-sm mb-2">Приглашение создано</h4>
          <p className="mb-3 text-emerald-400/80">{inviteMsg}</p>
          <p className="text-xs text-zinc-405">
            Передайте временный пароль новому участнику команды для входа.
          </p>
        </div>
      )}

      {notice === "invite-error" && (
        <div className="mb-6 p-4 rounded-xl border border-red-500/20 bg-red-500/10 text-red-300 text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0" />
          <span>Ошибка при отправке приглашения. Возможно, этот email уже зарегистрирован.</span>
        </div>
      )}

      {notice === "role-updated" && (
        <div className="mb-6 p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/10 text-emerald-300 text-sm">
          Роль участника успешно обновлена.
        </div>
      )}

      {notice === "role-error" && (
        <div className="mb-6 p-4 rounded-xl border border-red-500/20 bg-red-500/10 text-red-300 text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0" />
          <span>Не удалось обновить роль. Проверьте права доступа.</span>
        </div>
      )}

      {notice === "member-removed" && (
        <div className="mb-6 p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/10 text-emerald-300 text-sm">
          Участник успешно удален из команды.
        </div>
      )}

      {notice === "remove-error" && (
        <div className="mb-6 p-4 rounded-xl border border-red-500/20 bg-red-500/10 text-red-300 text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0" />
          <span>Не удалось удалить участника. Проверьте, не является ли он последним владельцем.</span>
        </div>
      )}

      {/* Members List */}
      <div className="rounded-2xl border border-white/5 bg-zinc-900/50 overflow-hidden mb-6">
        <div className="p-4 border-b border-white/5 flex items-center gap-2">
          <Users className="w-4 h-4 text-zinc-400" />
          <span className="text-sm font-medium text-zinc-300">Участники ({displayMembers.length})</span>
        </div>
        <div className="divide-y divide-white/5">
          {displayMembers.map((member) => {
            const roleInfo = roleLabels[member.role] || roleLabels.viewer;
            const isSelf = currentUser && member.id === currentUser.id;
            return (
              <div key={member.id} className="p-4 flex items-center justify-between hover:bg-white/[0.02] transition-colors">
                <div className="flex items-center gap-4 min-w-0">
                  <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center text-sm font-bold text-white flex-shrink-0 font-sans">
                    {member.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-white truncate">{member.name}</span>
                      {isSelf && (
                        <span className="px-2 py-0.5 rounded-full text-[9px] font-medium text-emerald-400 bg-emerald-400/10">
                          Вы
                        </span>
                      )}
                      {member.mfa_enabled && (
                        <span title="MFA включен">
                          <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-zinc-500">
                      <Mail className="w-3 h-3" />
                      <span className="truncate">{member.email}</span>
                      {!member.email_verified && (
                        <span className="text-amber-500 text-[10px]">• не подтверждён</span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  {isSelf ? (
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${roleInfo.color}`}>
                      {roleInfo.label}
                    </span>
                  ) : (
                    <div className="flex items-center gap-2">
                      <form action={updateTeamMemberRoleAction} className="flex items-center gap-1.5">
                        <input type="hidden" name="member_id" value={member.id} />
                        <select
                          name="role"
                          defaultValue={member.role}
                          className="rounded-lg border border-white/10 bg-zinc-800 px-2 py-1 text-xs text-white focus:outline-none focus:ring-1 focus:ring-emerald-500 font-sans"
                        >
                          <option value="viewer">Наблюдатель</option>
                          <option value="agent">Оператор</option>
                          <option value="admin">Админ</option>
                          <option value="owner">Владелец</option>
                        </select>
                        <SubmitButton
                          pendingText=".."
                          className="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-[10px] text-zinc-300 font-medium border border-white/5"
                        >
                          Изменить
                        </SubmitButton>
                      </form>

                      <form action={removeTeamMemberAction} className="inline">
                        <input type="hidden" name="member_id" value={member.id} />
                        <SubmitButton
                          pendingText="..."
                          className="p-2 rounded-lg text-zinc-500 hover:text-red-400 hover:bg-red-400/5 transition-colors flex items-center justify-center"
                          title="Удалить участника"
                        >
                          <Trash2 className="w-4 h-4" />
                        </SubmitButton>
                      </form>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Invite Form */}
      <InviteForm />

      {/* Roles Description */}
      <div className="mt-6 p-6 rounded-2xl border border-white/5 bg-zinc-900/50">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-4 h-4 text-blue-500" />
          <h3 className="text-sm font-medium text-zinc-400">Роли и права</h3>
        </div>
        <div className="grid sm:grid-cols-2 gap-3">
          <div className="text-sm">
            <span className="text-amber-400 font-medium">Владелец</span>
            <span className="text-zinc-500"> — все права, биллинг, удаление</span>
          </div>
          <div className="text-sm">
            <span className="text-blue-400 font-medium">Админ</span>
            <span className="text-zinc-500"> — агенты, знания, диалоги, аналитика</span>
          </div>
          <div className="text-sm">
            <span className="text-emerald-400 font-medium">Оператор</span>
            <span className="text-zinc-500"> — чтение агентов, диалоги, чаты</span>
          </div>
          <div className="text-sm">
            <span className="text-zinc-400 font-medium">Наблюдатель</span>
            <span className="text-zinc-500"> — только чтение</span>
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}
