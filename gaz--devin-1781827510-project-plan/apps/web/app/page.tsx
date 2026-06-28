import { 
  Phone, MessageSquare, Database, Zap, Workflow, ShieldCheck, 
  Check, ArrowRight, Activity, TerminalSquare, Play, Calculator, 
  Headphones, Store, Truck, Key, CheckCircle2, Globe, Cpu, X
} from "lucide-react";
import Link from "next/link";
import { HeaderNavigation } from "./components/HeaderNavigation";
import { CallTestForm } from "./components/CallTestForm";
const features = [
  {
    icon: <Phone className="h-5 w-5 text-zinc-100" />,
    title: "Реалистичные голосовые агенты",
    desc: "Задержка менее 800мс. Идеально справляется с перебиваниями, фоновым шумом и поддерживает естественный темп диалога.",
  },
  {
    icon: <Globe className="h-5 w-5 text-zinc-100" />,
    title: "Истинная омниканальность",
    desc: "Не только звонки. Тот же самый агент может консультировать клиентов в Telegram, ВКонтакте, WhatsApp или виджете на сайте.",
  },
  {
    icon: <Database className="h-5 w-5 text-zinc-100" />,
    title: "Векторные базы знаний",
    desc: "Загрузите PDF или укажите ссылку на сайт. Агент моментально проиндексирует данные через Qdrant и будет отвечать строго по регламенту.",
  },
  {
    icon: <Zap className="h-5 w-5 text-zinc-100" />,
    title: "Action Engine (Действия)",
    desc: "Интеграции с iiko, 1C, AmoCRM. Агенты могут выполнять API-запросы прямо во время разговора: например, забронировать стол или проверить склад.",
  },
  {
    icon: <Workflow className="h-5 w-5 text-zinc-100" />,
    title: "Динамический роутинг",
    desc: "Умное переключение между моделями GPT-4o, Claude 3.5 или локальным vLLM для достижения минимальной стоимости и максимальной скорости.",
  },
  {
    icon: <ShieldCheck className="h-5 w-5 text-zinc-100" />,
    title: "Enterprise Безопасность",
    desc: "Данные остаются в России (152-ФЗ). Маскировка персональных данных (PII) гарантирует отсутствие утечек в глобальные модели.",
  },
];

const comparison = [
  { feature: "Задержка в диалоге (Latency)", bland: "600-900мс", us: "600-800мс" },
  { feature: "Поддерживаемые каналы", bland: "Только телефония", us: "Телефон, VK, Telegram, Web" },
  { feature: "Свой ключ OpenAI (Без наценки)", bland: "Нет", us: "Да (BYOK)" },
  { feature: "Локальные интеграции", bland: "Только Webhooks", us: "iiko, 1C, AmoCRM, ЮKassa" },
  { feature: "Хранение данных", bland: "США", us: "Россия (152-ФЗ)" },
  { feature: "Омниканальная память", bland: "Нет", us: "Да" },
];

const pricing = [
  {
    name: "Start",
    price: "2 990",
    period: "₽ / мес",
    desc: "Для малого бизнеса, начинающего с автоматизации.",
    features: [
      "300 диалогов",
      "1 AI-агент",
      "Telegram и Web-виджет",
      "Поддержка BYOK (Свой API ключ)",
    ],
  },
  {
    name: "Business",
    price: "7 990",
    period: "₽ / мес",
    desc: "Для растущих команд, которым нужны голосовые роботы.",
    features: [
      "1 000 диалогов",
      "3 AI-агента (Голос + Текст)",
      "Интеграция с iiko и CRM",
      "До 3 пользователей в команде",
    ],
    featured: true,
  },
  {
    name: "Pro",
    price: "19 990",
    period: "₽ / мес",
    desc: "Для компаний с большим объемом обращений.",
    features: [
      "4 000 диалогов",
      "Безлимитное число каналов",
      "Кастомные сценарии (Workflows)",
      "Продвинутая аналитика",
    ],
  },
  {
    name: "Enterprise",
    price: "Индив.",
    period: "",
    desc: "Выделенная инфраструктура и поддержка 24/7.",
    features: [
      "Безлимитные диалоги",
      "SLA 99.9%",
      "Установка в ваш закрытый контур",
      "Собственные vLLM модели",
    ],
  },
];

type HomeProps = {
  searchParams?: Promise<{
    notice?: string;
  }>;
};

export default async function Home({ searchParams }: HomeProps) {
  const resolvedSearchParams = await searchParams;
  const notice = resolvedSearchParams?.notice;

  return (
    <main className="min-h-screen relative bg-black selection:bg-zinc-800 text-zinc-300 font-sans">
      {notice === "call-initiated" && (
        <div className="fixed top-4 right-4 z-50 bg-white text-black px-4 py-3 rounded border border-zinc-200 text-sm font-medium flex items-center gap-2 shadow-2xl">
          <Phone className="w-4 h-4" />
          Звонок успешно запущен.
        </div>
      )}
      {notice === "call-error" && (
        <div className="fixed top-4 right-4 z-50 bg-red-500 text-white px-4 py-3 rounded border border-red-600 text-sm font-medium flex items-center gap-2 shadow-2xl">
          <X className="w-4 h-4" />
          Ошибка при попытке позвонить.
        </div>
      )}

      {/* Navigation */}
      <HeaderNavigation />

      {/* Hero Section */}
      <section className="relative z-10 container mx-auto px-6 pt-24 pb-24 md:pt-32 md:pb-32 border-b border-white/10">
        <div className="grid xl:grid-cols-2 gap-16 items-start">
          <div className="max-w-2xl pt-8">
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-white mb-6 leading-[1.05]">
              Гиперреалистичные ИИ-агенты.
            </h1>
            <p className="text-xl md:text-2xl text-zinc-400 mb-10 max-w-xl leading-relaxed font-light">
              Любой голос, любой сценарий диалога, любой API. Создавайте и запускайте голосовых и чат-агентов Enterprise-уровня за считанные минуты.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <Link href="/register" className="inline-flex items-center justify-center gap-2 bg-white text-black px-6 py-3 rounded font-medium hover:bg-zinc-200 transition-colors">
                Начать разработку <ArrowRight className="w-4 h-4" />
              </Link>
              <Link href="/docs" className="inline-flex items-center justify-center gap-2 bg-transparent border border-white/20 text-white px-6 py-3 rounded font-medium hover:bg-white/5 transition-colors">
                Читать документацию
              </Link>
            </div>
          </div>

          {/* Strict Terminal Block */}
          <div className="relative w-full max-w-xl xl:ml-auto">
            <div className="rounded border border-white/10 bg-[#0a0a0a] overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-[#111]">
                <div className="text-xs font-mono text-zinc-500 uppercase tracking-widest">
                  Запустить звонок через API
                </div>
                <div className="flex gap-4 text-xs font-mono text-zinc-500">
                  <span className="text-white">cURL</span>
                  <span>Node</span>
                  <span>Python</span>
                </div>
              </div>
              
              <div className="p-6">
                <pre className="text-sm font-mono leading-relaxed overflow-x-auto text-zinc-400 mb-8">
                  curl -X POST https://api.callforce.ru/v1/calls \<br/>
                  &nbsp;&nbsp;-H <span className="text-zinc-100">"Authorization: Bearer sk-..."</span> \<br/>
                  &nbsp;&nbsp;-H <span className="text-zinc-100">"Content-Type: application/json"</span> \<br/>
                  &nbsp;&nbsp;-d '&#123;<br/>
                  &nbsp;&nbsp;&nbsp;&nbsp;<span className="text-zinc-100">"phone_number"</span>: <span className="text-zinc-100">"+79991234567"</span>,<br/>
                  &nbsp;&nbsp;&nbsp;&nbsp;<span className="text-zinc-100">"task"</span>: <span className="text-zinc-100">"Забронируй столик на вечер."</span>,<br/>
                  &nbsp;&nbsp;&nbsp;&nbsp;<span className="text-zinc-100">"voice"</span>: <span className="text-zinc-100">"ru-RU-female-1"</span><br/>
                  &nbsp;&nbsp;&#125;'
                </pre>

                <div className="border-t border-white/10 pt-6">
                  <h4 className="text-sm font-medium text-white mb-4">Или протестируйте ИИ, заказав звонок:</h4>
                  <CallTestForm />
                  <p className="text-xs text-zinc-500 mt-3">
                    Отправляя форму, вы соглашаетесь на прием автоматического вызова от ИИ.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-24 border-b border-white/10">
        <div className="container mx-auto px-6">
          <div className="max-w-3xl mb-16">
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-white mb-6">
              Инфраструктура Enterprise-уровня.
            </h2>
            <p className="text-zinc-400 text-lg">
              Построено для обработки миллионов диалогов. От SIP-транков с минимальной задержкой до интегрированных векторных БД — все работает "из коробки".
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-12">
            {features.map((f, i) => (
              <div key={i}>
                <div className="w-10 h-10 rounded bg-[#111] border border-white/10 flex items-center justify-center mb-5">
                  {f.icon}
                </div>
                <h3 className="text-lg font-medium text-white mb-2">{f.title}</h3>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  {f.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* BYOK Section */}
      <section id="byok" className="py-24 border-b border-white/10 bg-[#050505]">
        <div className="container mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-white mb-6">
                Используйте свой ключ. Ноль наценок.
              </h2>
              <p className="text-zinc-400 text-lg leading-relaxed mb-6">
                Большинство платформ берут огромную комиссию (markup) за генерацию токенов LLM. Мы — нет. Подключите свой API-ключ OpenAI, и оплачивайте ИИ по себестоимости провайдера.
              </p>
              <ul className="space-y-3">
                <li className="flex items-center gap-3 text-zinc-300">
                  <Check className="w-4 h-4 text-zinc-100" />
                  Никаких скрытых комиссий за токены
                </li>
                <li className="flex items-center gap-3 text-zinc-300">
                  <Check className="w-4 h-4 text-zinc-100" />
                  Полный доступ к GPT-4o и кастомным моделям
                </li>
                <li className="flex items-center gap-3 text-zinc-300">
                  <Check className="w-4 h-4 text-zinc-100" />
                  Сохраняете все соглашения с вашим провайдером
                </li>
              </ul>
            </div>
            <div className="p-8 rounded border border-white/10 bg-black">
              <div className="flex items-center justify-between mb-8 pb-8 border-b border-white/10">
                <div>
                  <div className="text-zinc-500 text-sm mb-1">Глобальные Аналоги</div>
                  <div className="text-white text-xl">Подписка + Наценка на Токены</div>
                </div>
                <X className="w-6 h-6 text-zinc-600" />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-zinc-500 text-sm mb-1">CallForce</div>
                  <div className="text-white text-xl">Платформа + Чистая цена провайдера</div>
                </div>
                <CheckCircle2 className="w-6 h-6 text-zinc-100" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Comparison Matrix vs Bland AI */}
      <section id="compare" className="py-24 border-b border-white/10">
        <div className="container mx-auto px-6 max-w-5xl">
          <div className="mb-16">
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-white mb-6">
              Сравнение платформ.
            </h2>
            <p className="text-zinc-400 text-lg">
              Посмотрите, почему компании мигрируют на CallForce ради локальных интеграций и отсутствия скрытых наценок.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/20">
                  <th className="py-4 pr-6 text-zinc-100 font-medium w-1/3">Функция</th>
                  <th className="py-4 px-6 text-zinc-500 font-medium w-1/3 border-l border-white/10">Глобальные Аналоги</th>
                  <th className="py-4 pl-6 text-white font-medium w-1/3 border-l border-white/10">CallForce</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {comparison.map((row, idx) => (
                  <tr key={idx} className="border-b border-white/10 last:border-0">
                    <td className="py-4 pr-6 text-zinc-400">{row.feature}</td>
                    <td className="py-4 px-6 text-zinc-500 border-l border-white/10">{row.bland}</td>
                    <td className="py-4 pl-6 text-white border-l border-white/10">{row.us}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Integrations Minimal */}
      <section id="integrations" className="py-24 border-b border-white/10 bg-[#050505]">
        <div className="container mx-auto px-6">
          <div className="max-w-2xl mb-16">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-4">
              Нативные интеграции.
            </h2>
            <p className="text-zinc-400 text-lg">
              Запускайте действия и запрашивайте контекст прямо во время диалога.
            </p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {[
              "iiko", "1C:Предприятие", "AmoCRM", "Bitrix24", "Telegram", "ВКонтакте",
              "ЮKassa", "Asterisk (SIP)", "Twilio", "r_keeper", "Google Calendar", "Qdrant"
            ].map((integration) => (
              <div key={integration} className="flex items-center justify-center p-4 rounded border border-white/10 bg-black text-sm text-zinc-400 hover:text-white transition-colors cursor-pointer text-center">
                {integration}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 border-b border-white/10">
        <div className="container mx-auto px-6">
          <div className="mb-16">
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-white mb-6">
              Прозрачные тарифы.
            </h2>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {pricing.map((p, i) => (
              <div
                key={i}
                className={`p-8 rounded border ${p.featured ? "border-white bg-[#111]" : "border-white/10 bg-black"} flex flex-col`}
              >
                <div className="text-lg font-medium text-white mb-2">{p.name}</div>
                <div className="flex items-baseline gap-1 mb-4">
                  <span className="text-3xl font-bold text-white">{p.price}</span>
                  <span className="text-xs text-zinc-500 uppercase tracking-widest">{p.period}</span>
                </div>
                <p className="text-sm text-zinc-400 mb-8 pb-8 border-b border-white/10">{p.desc}</p>

                <ul className="space-y-4 mb-8 flex-1">
                  {p.features.map((feature, fIdx) => (
                    <li key={fIdx} className="flex items-start gap-3 text-sm text-zinc-300">
                      <Check className="w-4 h-4 text-zinc-500 shrink-0 mt-0.5" />
                      {feature}
                    </li>
                  ))}
                </ul>

                <Link
                  href="/register"
                  className={`block w-full text-center py-2.5 rounded font-medium transition-colors text-sm ${
                    p.featured
                      ? 'bg-white text-black hover:bg-zinc-200'
                      : 'bg-transparent border border-white/20 text-white hover:bg-white/10'
                  }`}
                >
                  Начать бесплатно
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 bg-black">
        <div className="container mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 bg-white text-black flex items-center justify-center font-bold text-[10px]">CF</div>
            <span className="text-sm text-zinc-500">© 2026 CallForce Inc.</span>
          </div>
          <div className="flex gap-6 text-sm text-zinc-500">
            <Link href="/docs" className="hover:text-white transition-colors">API Документация</Link>
            <Link href="/privacy" className="hover:text-white transition-colors">Конфиденциальность (152-ФЗ)</Link>
            <Link href="/terms" className="hover:text-white transition-colors">Условия использования</Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
