import { DashboardShell } from "../../components/DashboardShell";
import { fetchCoreApi } from "../../../lib/core-api";
import { Key, Plus, Copy, Trash2, Clock, Shield } from "lucide-react";

type ApiKeyItem = {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  created_at: string;
  last_used_at: string | null;
  revoked: boolean;
};

async function getApiKeys(): Promise<ApiKeyItem[]> {
  const result = await fetchCoreApi<ApiKeyItem[]>("/api/v1/api-keys");
  if (result.state === "live") return result.data;
  return [];
}

function CreateKeyForm() {
  return (
    <div className="p-6 rounded-2xl border border-white/5 bg-zinc-900/50">
      <div className="flex items-center gap-2 mb-4">
        <Plus className="w-4 h-4 text-emerald-500" />
        <h3 className="text-sm font-medium text-zinc-400">Создать API ключ</h3>
      </div>
      <form className="space-y-4">
        <div>
          <label htmlFor="key-name" className="block text-xs font-medium text-zinc-400 mb-1.5">Название</label>
          <input
            id="key-name"
            name="name"
            type="text"
            required
            placeholder="Production Bot, Staging Integration..."
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>
        <div className="flex items-end gap-4">
          <div className="flex-1">
            <label htmlFor="key-scopes" className="block text-xs font-medium text-zinc-400 mb-1.5">Доступ</label>
            <select
              id="key-scopes"
              name="scopes"
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            >
              <option value="read">Только чтение</option>
              <option value="read,write">Чтение + запись</option>
              <option value="read,write,admin">Полный доступ</option>
            </select>
          </div>
          <button
            type="submit"
            className="px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-500 transition-colors whitespace-nowrap"
          >
            Создать ключ
          </button>
        </div>
      </form>
    </div>
  );
}

export default async function ApiKeysPage() {
  const keys = await getApiKeys();

  // Demo data fallback
  const displayKeys: ApiKeyItem[] = keys.length > 0 ? keys : [
    {
      id: "1",
      name: "Production Bot",
      key_prefix: "cf_live_abc1...",
      scopes: ["read", "write"],
      created_at: new Date(Date.now() - 7 * 86400000).toISOString(),
      last_used_at: new Date(Date.now() - 3600000).toISOString(),
      revoked: false,
    },
    {
      id: "2",
      name: "Staging Test",
      key_prefix: "cf_live_xyz9...",
      scopes: ["read"],
      created_at: new Date(Date.now() - 30 * 86400000).toISOString(),
      last_used_at: null,
      revoked: true,
    },
  ];

  return (
    <DashboardShell
      activePath="/settings/api-keys"
      eyebrow="Настройки"
      title="API Ключи"
      description="Управляйте ключами для программного доступа к API"
    >
      {/* Keys List */}
      <div className="rounded-2xl border border-white/5 bg-zinc-900/50 overflow-hidden mb-6">
        <div className="p-4 border-b border-white/5 flex items-center gap-2">
          <Key className="w-4 h-4 text-zinc-400" />
          <span className="text-sm font-medium text-zinc-300">Ключи ({displayKeys.length})</span>
        </div>

        {displayKeys.length === 0 ? (
          <div className="p-8 text-center text-sm text-zinc-500">
            Нет API ключей. Создайте первый ключ ниже.
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {displayKeys.map((apiKey) => (
              <div key={apiKey.id} className={`p-4 flex items-center justify-between hover:bg-white/[0.02] transition-colors ${apiKey.revoked ? 'opacity-50' : ''}`}>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-white">{apiKey.name}</span>
                    {apiKey.revoked && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-medium text-red-400 bg-red-400/10">
                        Отозван
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-zinc-500">
                    <span className="font-mono bg-white/5 px-2 py-0.5 rounded text-zinc-400">
                      {apiKey.key_prefix}
                    </span>
                    <span className="flex items-center gap-1">
                      <Shield className="w-3 h-3" />
                      {apiKey.scopes.join(", ")}
                    </span>
                    {apiKey.last_used_at && (
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        Использован: {new Date(apiKey.last_used_at).toLocaleDateString("ru-RU")}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0 ml-4">
                  {!apiKey.revoked && (
                    <>
                      <button
                        className="p-2 rounded-lg text-zinc-500 hover:text-white hover:bg-white/5 transition-colors"
                        title="Копировать префикс"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                      <button
                        className="p-2 rounded-lg text-zinc-500 hover:text-red-400 hover:bg-red-400/5 transition-colors"
                        title="Отозвать ключ"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Form */}
      <CreateKeyForm />

      {/* Usage Info */}
      <div className="mt-6 p-6 rounded-2xl border border-white/5 bg-zinc-900/50">
        <h3 className="text-sm font-medium text-zinc-400 mb-3">Как использовать</h3>
        <pre className="text-xs font-mono text-zinc-400 bg-black/50 rounded-lg p-4 overflow-x-auto">
{`curl -H "Authorization: Bearer cf_live_YOUR_KEY" \\
     https://api.callforce.ru/api/v1/agents`}
        </pre>
        <p className="text-xs text-zinc-500 mt-3">
          API ключ показывается только при создании. Храните его в безопасном месте.
        </p>
      </div>

      {keys.length === 0 && (
        <p className="text-xs text-zinc-600 mt-4 text-center">
          Показаны demo-данные. Подключите API для управления ключами.
        </p>
      )}
    </DashboardShell>
  );
}
