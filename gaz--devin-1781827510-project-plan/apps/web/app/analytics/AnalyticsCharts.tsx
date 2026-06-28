"use client";

import { BarChart, Bar, XAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie } from "recharts";
import { DailyConversation, ChannelBreakdown } from "../../lib/mvp-data";

export function MiniBarChart({ data }: { data: DailyConversation[] }) {
  const recent = data.slice(-14);

  return (
    <div className="p-6 rounded-2xl border border-white/5 bg-zinc-900/50">
      <h3 className="text-sm font-medium text-zinc-400 mb-4">Диалоги за последние 14 дней</h3>
      <div className="h-40 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={recent}>
            <XAxis dataKey="date" tickFormatter={(val) => val.slice(5)} stroke="#52525b" fontSize={10} tickLine={false} axisLine={false} />
            <Tooltip
              cursor={{ fill: '#3f3f46', opacity: 0.4 }}
              contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', color: '#fff' }}
              itemStyle={{ color: '#10b981' }}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {recent.map((entry, index) => (
                <Cell key={`cell-${index}`} fill="#10b981" />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function ChannelList({ channels }: { channels: ChannelBreakdown[] }) {
  const channelNames: Record<string, string> = {
    telegram: "Telegram",
    web_widget: "Web Widget",
    whatsapp: "WhatsApp",
    vk: "VK",
    sip: "SIP / Телефон",
    voice: "Голос",
  };
  
  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#71717a'];

  const formattedData = channels.map(c => ({
    name: channelNames[c.channel] || c.channel,
    value: c.count
  }));

  return (
    <div className="p-6 rounded-2xl border border-white/5 bg-zinc-900/50">
      <h3 className="text-sm font-medium text-zinc-400 mb-4">Каналы (распределение)</h3>
      <div className="h-40 w-full flex items-center">
        {channels.length === 0 ? (
          <p className="text-sm text-zinc-500 w-full text-center">Нет данных</p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={formattedData}
                cx="50%"
                cy="50%"
                innerRadius={40}
                outerRadius={60}
                paddingAngle={5}
                dataKey="value"
              >
                {formattedData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', color: '#fff' }}
                itemStyle={{ color: '#fff' }}
              />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
