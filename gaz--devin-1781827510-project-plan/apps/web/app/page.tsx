import { Phone, MessageSquare, Database, Zap, Workflow, ShieldCheck, Check, ArrowRight, Activity, TerminalSquare, Play } from "lucide-react";
import Link from "next/link";
import { MotionDiv } from "./components/MotionWrapper";

const features = [
  {
    icon: <Phone className="h-6 w-6 text-zinc-100" />,
    title: "Голосовые AI-агенты",
    desc: "Входящие и исходящие звонки через SIP. Cold calling, горячие линии, поддержка — 24/7 без операторов.",
  },
  {
    icon: <MessageSquare className="h-6 w-6 text-zinc-100" />,
    title: "Чат-агенты",
    desc: "Telegram, WhatsApp, VK, web-виджет. Единая модель диалога для всех каналов связи с клиентом.",
  },
  {
    icon: <Database className="h-6 w-6 text-zinc-100" />,
    title: "RAG база знаний",
    desc: "Загрузите документы — агент отвечает по ним с цитатами. Интеграция с Qdrant vector search.",
  },
  {
    icon: <Zap className="h-6 w-6 text-zinc-100" />,
    title: "Action Engine",
    desc: "iiko, r_keeper, AmoCRM, Bitrix24, 1C. Агент выполняет действия, а не просто отвечает на вопросы.",
  },
  {
    icon: <Workflow className="h-6 w-6 text-zinc-100" />,
    title: "Визуальный роутинг",
    desc: "LLM-роутинг между пограничными моделями (GPT-4o, Claude) и локальными (vLLM) для снижения latency.",
  },
  {
    icon: <ShieldCheck className="h-6 w-6 text-zinc-100" />,
    title: "Enterprise Security",
    desc: "Multi-tenant архитектура, изолированные контуры, 152-ФЗ compliance, PII masking.",
  },
];

const advantages = [
  {
    label: "Каналы",
    value: "6+ каналов",
    compare: "Bland.ai — только телефон",
  },
  {
    label: "Языки",
    value: "RU + EN + multi",
    compare: "Bland.ai — только English",
  },
  {
    label: "Интеграции",
    value: "iiko, CRM, 1C, ЮKassa",
    compare: "Bland.ai — webhooks only",
  },
  {
    label: "Интерфейс",
    value: "SaaS Dashboard",
    compare: "Bland.ai — только API",
  },
];

const pricing = [
  {
    name: "Start",
    price: "2 990",
    period: "₽/мес",
    desc: "Для малого бизнеса",
    features: [
      "300 диалогов/мес",
      "1 AI-агент",
      "Telegram + виджет",
      "Базовая аналитика",
    ],
  },
  {
    name: "Business",
    price: "7 990",
    period: "₽/мес",
    desc: "Для растущего бизнеса",
    features: [
      "1 000 диалогов/мес",
      "3 агента + голос",
      "iiko интеграция",
      "3 пользователя",
    ],
    featured: true,
  },
  {
    name: "Pro",
    price: "19 990",
    period: "₽/мес",
    desc: "Для серьёзных команд",
    features: [
      "4 000 диалогов/мес",
      "10 каналов",
      "CRM + сценарии",
      "Продвинутая аналитика",
    ],
  },
  {
    name: "Enterprise",
    price: "Индив.",
    period: "",
    desc: "Выделенный контур",
    features: [
      "Безлимит диалогов",
      "SLA 99.9%",
      "SSO + On-premise",
      "Свои модели",
    ],
  },
];

export default function Home() {
  return (
    <main className="min-h-screen relative overflow-hidden bg-black selection:bg-zinc-800">
      {/* Background glow effects */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden flex items-center justify-center">
        <div className="absolute top-[-20%] right-[-10%] w-[600px] h-[600px] bg-zinc-800 rounded-full blur-[120px] opacity-30 animate-pulse"></div>
        <div className="absolute bottom-[-20%] left-[-10%] w-[500px] h-[500px] bg-zinc-900 rounded-full blur-[120px] opacity-40"></div>
      </div>

      {/* Navigation */}
      <header className="sticky top-0 z-50 w-full border-b border-white/5 bg-black/40 backdrop-blur-xl">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-white text-black flex items-center justify-center font-bold text-sm tracking-tighter">
              CF
            </div>
            <span className="font-bold text-lg tracking-tight text-white">
              CallForce
            </span>
          </div>
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-zinc-400">
            <a href="#features" className="hover:text-white transition-colors">Платформа</a>
            <a href="#advantages" className="hover:text-white transition-colors">Сравнение</a>
            <a href="#pricing" className="hover:text-white transition-colors">Тарифы</a>
            <a href="#faq" className="hover:text-white transition-colors">FAQ</a>
          </nav>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors hidden sm:block">
              Войти
            </Link>
            <Link href="/register" className="text-sm font-medium bg-white text-black px-4 py-2 rounded-md hover:bg-zinc-200 transition-colors">
              Создать агента
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative z-10 container mx-auto px-6 pt-32 pb-24 md:pt-48 md:pb-32">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          <MotionDiv className="max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/10 bg-white/5 text-xs font-medium text-zinc-300 mb-8 backdrop-blur-md">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              API & Dashboard Доступны
            </div>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tighter text-white mb-6 leading-[1.1]">
              Автоматизируйте <span className="text-zinc-500">звонки</span> и <span className="text-zinc-500">чаты</span> с помощью ИИ.
            </h1>
            <p className="text-lg md:text-xl text-zinc-400 mb-10 max-w-xl leading-relaxed">
              Создавайте, тестируйте и запускайте диалоговых ИИ-агентов за минуты.
              Бесшовная интеграция с российскими CRM, 152-ФЗ compliance и отклик быстрее секунды.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <Link href="/register" className="inline-flex items-center justify-center gap-2 bg-white text-black px-6 py-3 rounded-md font-medium hover:bg-zinc-200 transition-colors">
                Начать бесплатно <ArrowRight className="w-4 h-4" />
              </Link>
              <a href="#features" className="inline-flex items-center justify-center gap-2 bg-transparent border border-white/10 text-white px-6 py-3 rounded-md font-medium hover:bg-white/5 transition-colors">
                Смотреть возможности
              </a>
            </div>
          </MotionDiv>

          {/* Hero Terminal/Code Block Visual */}
          <div className="relative">
            <div className="premium-border bg-black/60 backdrop-blur-2xl p-6 shadow-2xl">
              <div className="flex items-center justify-between mb-6 border-b border-white/10 pb-4">
                <div className="flex gap-2">
                  <div className="w-3 h-3 rounded-full bg-zinc-800"></div>
                  <div className="w-3 h-3 rounded-full bg-zinc-800"></div>
                  <div className="w-3 h-3 rounded-full bg-zinc-800"></div>
                </div>
                <div className="text-xs font-mono text-zinc-500">agent.py</div>
              </div>
              <pre className="text-sm font-mono text-zinc-300 overflow-x-auto leading-relaxed">
                <code className="block mb-2"><span className="text-emerald-400">import</span> callforce</code>
                <code className="block mb-2"></code>
                <code className="block mb-2">agent = callforce.Agent(</code>
                <code className="block mb-2">  name=<span className="text-amber-300">&quot;Sales Rep&quot;</span>,</code>
                <code className="block mb-2">  prompt=<span className="text-amber-300">&quot;Book a table for the user.&quot;</span>,</code>
                <code className="block mb-2">  tools=[<span className="text-amber-300">&quot;iiko.book_table&quot;</span>]</code>
                <code className="block mb-2">)</code>
                <code className="block mb-2"></code>
                <code className="block mb-2">agent.deploy(channels=[<span className="text-amber-300">&quot;telegram&quot;</span>, <span className="text-amber-300">&quot;sip&quot;</span>])</code>
                <code className="block mb-2 text-zinc-600">{"# => Agent deployed to +7 (495) 123-45-67"}</code>
              </pre>

              <div className="mt-8 pt-6 border-t border-white/10 grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-zinc-500 font-mono mb-1">LATENCY</div>
                  <div className="text-white font-mono flex items-center gap-2">
                    <Activity className="w-4 h-4 text-emerald-500" />
                    ~800ms
                  </div>
                </div>
                <div>
                  <div className="text-xs text-zinc-500 font-mono mb-1">ROUTER</div>
                  <div className="text-white font-mono flex items-center gap-2">
                    <TerminalSquare className="w-4 h-4 text-blue-500" />
                    vLLM / GPT-4o
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Product Video Demo Preview */}
      <section className="relative z-10 container mx-auto px-6 pb-24">
        <div className="max-w-5xl mx-auto rounded-3xl border border-white/10 bg-zinc-900/40 p-4 backdrop-blur-3xl shadow-[0_20px_50px_rgba(0,0,0,0.8)] overflow-hidden">
          <div className="relative aspect-video rounded-2xl overflow-hidden bg-black flex items-center justify-center group cursor-pointer border border-white/5">
            <div className="absolute inset-0 bg-gradient-to-tr from-black via-zinc-950/60 to-transparent z-10" />
            <div className="absolute inset-0 z-0 bg-[radial-gradient(#1c1c1c_1px,transparent_1px)] [background-size:16px_16px] opacity-40" />
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20 flex flex-col items-center gap-4">
              <div className="w-20 h-20 rounded-full bg-white text-black flex items-center justify-center shadow-[0_0_30px_rgba(255,255,255,0.4)] group-hover:scale-110 transition-transform duration-500">
                <Play className="w-8 h-8 fill-current ml-1" />
              </div>
              <span className="text-white font-semibold text-sm md:text-base tracking-widest uppercase">Смотреть демо CallForce (2 мин)</span>
            </div>
            <div className="absolute -bottom-20 -left-20 w-80 h-80 rounded-full bg-zinc-800/20 blur-[80px] group-hover:bg-zinc-800/40 transition-colors duration-500" />
            <div className="absolute -top-20 -right-20 w-80 h-80 rounded-full bg-white/5 blur-[80px] group-hover:bg-white/10 transition-colors duration-500" />
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="relative z-10 py-24 border-t border-white/5 bg-zinc-950">
        <div className="container mx-auto px-6">
          <div className="max-w-2xl mb-16">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-4">
              Инфраструктура для ИИ-Агентов
            </h2>
            <p className="text-zinc-400 text-lg">
              Всё необходимое для запуска AI-агентов в продакшене: от миллисекундной задержки в голосе до умных баз знаний.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f, i) => (
              <MotionDiv key={i} delay={i * 0.1} className="p-6 rounded-2xl border border-white/5 bg-zinc-900/50 hover:bg-zinc-900 transition-colors">
                <div className="w-12 h-12 rounded-lg bg-zinc-800 flex items-center justify-center mb-6 border border-white/5">
                  {f.icon}
                </div>
                <h3 className="text-lg font-semibold text-white mb-3">{f.title}</h3>
                <p className="text-zinc-400 leading-relaxed text-sm">
                  {f.desc}
                </p>
              </MotionDiv>
            ))}
          </div>
        </div>
      </section>

      {/* Advantages vs Competitors */}
      <section id="advantages" className="relative z-10 py-24 border-t border-white/5 bg-black">
        <div className="container mx-auto px-6">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-6">
                Создано для локального рынка.
              </h2>
              <p className="text-zinc-400 text-lg mb-8">
                Глобальные инструменты вроде Bland.ai — это отлично. Но они не понимают наш контекст, не интегрируются с локальным ПО (iiko, 1С) и не соблюдают 152-ФЗ.
              </p>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              {advantages.map((adv, idx) => (
                <div key={idx} className="p-6 rounded-xl border border-white/5 bg-zinc-900/50">
                  <div className="text-xs font-mono text-zinc-500 mb-2 uppercase tracking-wider">{adv.label}</div>
                  <div className="text-xl font-bold text-white mb-2">{adv.value}</div>
                  <div className="text-sm text-zinc-500">{adv.compare}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="relative z-10 py-24 border-t border-white/5 bg-zinc-950">
        <div className="container mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-4">
              Прозрачные тарифы
            </h2>
            <p className="text-zinc-400 text-lg">
              Начинайте бесплатно, масштабируйтесь бесконечно. Платите только за то, что используете.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {pricing.map((p, i) => (
              <MotionDiv
                key={i}
                delay={i * 0.1}
                className={`relative p-8 rounded-2xl border ${p.featured ? "border-emerald-500/50 bg-emerald-500/5" : "border-white/5 bg-zinc-900/50"} flex flex-col`}
              >
                {p.featured && (
                  <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white text-black text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
                    Самый популярный
                  </div>
                )}
                <div className="text-lg font-medium text-white mb-2">{p.name}</div>
                <div className="flex items-baseline gap-1 mb-2">
                  <span className="text-3xl font-bold text-white">{p.price}</span>
                  <span className="text-sm text-zinc-500">{p.period}</span>
                </div>
                <p className="text-sm text-zinc-400 mb-8">{p.desc}</p>

                <ul className="space-y-4 mb-8 flex-1">
                  {p.features.map((feature, fIdx) => (
                    <li key={fIdx} className="flex items-center gap-3 text-sm text-zinc-300">
                      <Check className="w-4 h-4 text-emerald-500 shrink-0" />
                      {feature}
                    </li>
                  ))}
                </ul>

                <Link
                  href="/register"
                  className={`block w-full text-center py-3 rounded-lg font-medium transition-colors ${
                    p.featured
                      ? 'bg-white text-black hover:bg-zinc-200'
                      : 'bg-white/5 text-white hover:bg-white/10'
                  }`}
                >
                  {p.featured ? 'Начать бесплатно' : 'Выбрать тариф'}
                </Link>
              </MotionDiv>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="relative z-10 py-24 border-t border-white/5 bg-black">
        <div className="container mx-auto px-6 max-w-4xl">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-4">
              Часто задаваемые вопросы (FAQ)
            </h2>
            <p className="text-zinc-400 text-lg">
              Ответы на популярные вопросы о внедрении ИИ-ассистентов в рестораны и доставку.
            </p>
          </div>

          <div className="space-y-4">
            <details className="group border border-white/5 bg-white/[0.01] rounded-2xl overflow-hidden [&_summary::-webkit-details-marker]:hidden">
              <summary className="flex items-center justify-between gap-1.5 p-6 text-white cursor-pointer select-none">
                <h3 className="font-semibold text-base md:text-lg">Как быстро ИИ-агент отвечает на звонки?</h3>
                <span className="relative h-5 w-5 shrink-0">
                  <svg className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-5 w-5 text-white transition duration-300 group-open:-rotate-180" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </span>
              </summary>
              <div className="px-6 pb-6 text-zinc-400 text-sm leading-relaxed border-t border-white/5 pt-4 bg-black/40">
                Благодаря архитектуре WebSocket и оптимизированному роутингу, latency (задержка) ответов составляет от 600 до 1200 мс. Человек не замечает пауз и ощущает разговор как естественный диалог в реальном времени.
              </div>
            </details>

            <details className="group border border-white/5 bg-white/[0.01] rounded-2xl overflow-hidden [&_summary::-webkit-details-marker]:hidden">
              <summary className="flex items-center justify-between gap-1.5 p-6 text-white cursor-pointer select-none">
                <h3 className="font-semibold text-base md:text-lg">Можно ли загрузить наше собственное меню и акции?</h3>
                <span className="relative h-5 w-5 shrink-0">
                  <svg className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-5 w-5 text-white transition duration-300 group-open:-rotate-180" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </span>
              </summary>
              <div className="px-6 pb-6 text-zinc-400 text-sm leading-relaxed border-t border-white/5 pt-4 bg-black/40">
                Да! Для этого предназначен инструмент RAG (Retrieval-Augmented Generation). Вы загружаете PDF-файл с меню или указываете ссылку на сайт, система автоматически индексирует данные в векторную БД Qdrant, и ИИ использует их при ответах.
              </div>
            </details>

            <details className="group border border-white/5 bg-white/[0.01] rounded-2xl overflow-hidden [&_summary::-webkit-details-marker]:hidden">
              <summary className="flex items-center justify-between gap-1.5 p-6 text-white cursor-pointer select-none">
                <h3 className="font-semibold text-base md:text-lg">Как работает перевод диалога на оператора?</h3>
                <span className="relative h-5 w-5 shrink-0">
                  <svg className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-5 w-5 text-white transition duration-300 group-open:-rotate-180" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </span>
              </summary>
              <div className="px-6 pb-6 text-zinc-400 text-sm leading-relaxed border-t border-white/5 pt-4 bg-black/40">
                Если клиент просит позвать менеджера или задает нестандартный вопрос, ИИ-агент автоматически активирует инструмент `escalate_to_human`. Система присылает уведомление в operator panel, и реальный сотрудник подключается к диалогу.
              </div>
            </details>

            <details className="group border border-white/5 bg-white/[0.01] rounded-2xl overflow-hidden [&_summary::-webkit-details-marker]:hidden">
              <summary className="flex items-center justify-between gap-1.5 p-6 text-white cursor-pointer select-none">
                <h3 className="font-semibold text-base md:text-lg">Соответствует ли CallForce закону 152-ФЗ?</h3>
                <span className="relative h-5 w-5 shrink-0">
                  <svg className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-5 w-5 text-white transition duration-300 group-open:-rotate-180" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </span>
              </summary>
              <div className="px-6 pb-6 text-zinc-400 text-sm leading-relaxed border-t border-white/5 pt-4 bg-black/40">
                Да, персональные данные клиентов хранятся исключительно в изолированных серверах на территории РФ. Перед передачей данных в LLM-модели происходит маскирование PII (номеров телефонов, адресов, фамилий), что исключает утечки.
              </div>
            </details>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-12 bg-black">
        <div className="container mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-zinc-800 text-zinc-400 flex items-center justify-center font-bold text-[10px]">CF</div>
            <span className="text-sm text-zinc-500">© 2026 CallForce Inc.</span>
          </div>
          <div className="flex gap-6 text-sm text-zinc-500">
            <Link href="/docs" className="hover:text-white transition-colors">Документация</Link>
            <Link href="/privacy" className="hover:text-white transition-colors">Конфиденциальность (152-ФЗ)</Link>
            <Link href="/terms" className="hover:text-white transition-colors">Оферта</Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
