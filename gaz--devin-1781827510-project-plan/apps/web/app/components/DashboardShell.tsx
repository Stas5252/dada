import Link from "next/link";
import type { ReactNode } from "react";
import { LayoutDashboard, CheckSquare, Bot, Database, TerminalSquare, MessageSquare, LogOut, ArrowLeft, Menu, ShieldCheck, BarChart3, Users, Key, Radio, ClipboardList, Headset, CreditCard } from "lucide-react";
import { logoutAction } from "../actions";

const navigation = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/agents", label: "AI-Агенты", icon: Bot },
  { href: "/knowledge", label: "База Знаний", icon: Database },
  { href: "/conversations", label: "Диалоги", icon: MessageSquare },
  { href: "/operator", label: "Консоль оператора", icon: Headset },
  { href: "/analytics", label: "Аналитика", icon: BarChart3 },
  { href: "/billing", label: "Тарифы и биллинг", icon: CreditCard },
  { href: "/test-console", label: "Test Console", icon: TerminalSquare },
  { href: "/onboarding", label: "Чеклист", icon: CheckSquare },
  { href: "/settings/channels", label: "Каналы связи", icon: Radio },
  { href: "/settings/team", label: "Команда", icon: Users },
  { href: "/settings/api-keys", label: "API Ключи", icon: Key },
  { href: "/settings/security", label: "Security", icon: ShieldCheck },
  { href: "/settings/audit", label: "Журнал аудита", icon: ClipboardList },
];

type DashboardShellProps = {
  activePath: string;
  eyebrow: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
};

export function DashboardShell({
  activePath,
  eyebrow,
  title,
  description,
  actions,
  children,
}: DashboardShellProps) {
  return (
    <div className="flex min-h-screen bg-black">
      {/* Sidebar */}
      <aside className="hidden w-64 flex-shrink-0 border-r border-white/5 bg-zinc-950 md:flex md:flex-col">
        <div className="h-16 flex items-center px-6 border-b border-white/5">
          <Link className="flex items-center gap-3 group" href="/dashboard">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-indigo-600 text-white flex items-center justify-center font-bold text-sm tracking-tighter shadow-lg shadow-purple-500/20 group-hover:shadow-purple-500/40 transition-shadow duration-300 status-dot-online">
              CF
            </div>
            <span className="font-bold text-lg tracking-tight text-white">
              CallForce
            </span>
          </Link>
        </div>

        <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
          <div className="text-[10px] font-mono text-zinc-600 mb-3 uppercase tracking-[0.2em] px-3">
            Workspace
          </div>
          {navigation.map((item) => {
            const isActive = item.href === activePath;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? "bg-white/[0.08] text-white nav-active-indicator"
                    : "text-zinc-400 hover:text-white hover:bg-white/[0.04]"
                }`}
              >
                <item.icon className={`h-4 w-4 transition-colors ${isActive ? "text-purple-400" : "text-zinc-500 group-hover:text-zinc-300"}`} />
                {item.label}
                {isActive && (
                  <div className="ml-auto w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
                )}
              </Link>
            );
          })}
        </nav>

        <div className="p-3 border-t border-white/5 space-y-1">
          <Link href="/" className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-zinc-400 hover:text-white hover:bg-white/[0.04] transition-all duration-200">
            <ArrowLeft className="h-4 w-4 text-zinc-500" />
            На главную
          </Link>
          <form action={logoutAction}>
            <button type="submit" className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-zinc-400 hover:text-white hover:bg-white/[0.04] transition-all duration-200">
              <LogOut className="h-4 w-4 text-zinc-500" />
              Выйти
            </button>
          </form>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-black">
        <div className="border-b border-white/5 bg-zinc-950 md:hidden">
          <div className="flex h-16 items-center justify-between px-4">
            <Link className="flex items-center gap-3" href="/dashboard">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-indigo-600 text-white flex items-center justify-center font-bold text-sm tracking-tighter shadow-lg shadow-purple-500/20">
                CF
              </div>
              <span className="font-bold text-lg tracking-tight text-white">
                CallForce
              </span>
            </Link>
            <details className="relative">
              <summary
                aria-label="Открыть меню"
                className="flex h-10 w-10 cursor-pointer list-none items-center justify-center rounded-lg border border-white/10 bg-white/5 text-zinc-300 transition-colors hover:bg-white/10 hover:text-white [&::-webkit-details-marker]:hidden"
              >
                <Menu className="h-5 w-5" />
              </summary>
              <div className="absolute right-0 top-12 z-50 w-[min(20rem,calc(100vw-2rem))] rounded-xl border border-white/10 bg-zinc-950 p-2 shadow-2xl backdrop-blur-xl">
                <nav className="space-y-0.5">
                  {navigation.map((item) => {
                    const isActive = item.href === activePath;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                          isActive
                            ? "bg-white/[0.08] text-white"
                            : "text-zinc-400 hover:bg-white/[0.04] hover:text-white"
                        }`}
                      >
                        <item.icon className={`h-4 w-4 ${isActive ? "text-purple-400" : "text-zinc-500"}`} />
                        {item.label}
                      </Link>
                    );
                  })}
                </nav>
                <div className="mt-2 space-y-0.5 border-t border-white/5 pt-2">
                  <Link href="/" className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-zinc-400 transition-all duration-200 hover:bg-white/[0.04] hover:text-white">
                    <ArrowLeft className="h-4 w-4 text-zinc-500" />
                    На главную
                  </Link>
                  <form action={logoutAction}>
                    <button type="submit" className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium text-zinc-400 transition-all duration-200 hover:bg-white/[0.04] hover:text-white">
                      <LogOut className="h-4 w-4 text-zinc-500" />
                      Выйти
                    </button>
                  </form>
                </div>
              </div>
            </details>
          </div>
        </div>

        <header className="flex-shrink-0 flex flex-col gap-3 px-4 py-3 border-b border-white/5 bg-zinc-950/50 backdrop-blur-md sm:h-16 sm:flex-row sm:items-center sm:justify-between sm:px-6 md:px-8">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full uppercase tracking-[0.15em] border border-emerald-500/20">
              {eyebrow}
            </span>
          </div>
          {actions && <div className="flex items-center gap-3">{actions}</div>}
        </header>

        <div className="flex-1 overflow-auto">
          <div className="p-4 sm:p-6 md:p-8 max-w-6xl mx-auto animate-fade-up">
            <div className="mb-8">
              <h1 className="text-3xl font-bold tracking-tight text-white mb-2">{title}</h1>
              {description && <p className="text-zinc-400 text-lg leading-relaxed">{description}</p>}
            </div>
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
