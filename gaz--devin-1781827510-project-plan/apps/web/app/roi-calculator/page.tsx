"use client";

import { useState, useMemo } from "react";
import {
  Calculator,
  Users,
  Phone,
  MessageSquare,
  Clock,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { MotionDiv } from "../components/MotionWrapper";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from "recharts";

/* ── Industry presets ────────────────────────────────────────────── */
type Industry = "restaurant" | "clinic" | "ecommerce" | "delivery" | "services";

const PRESETS: Record<Industry, { label: string; callsPerDay: number; chatsPerDay: number; avgCallMinutes: number; operatorSalary: number; operatorsCount: number; automationTarget: number }> = {
  restaurant: {
    label: "Ресторан / Доставка",
    callsPerDay: 120,
    chatsPerDay: 80,
    avgCallMinutes: 2.5,
    operatorSalary: 55000,
    operatorsCount: 4,
    automationTarget: 75,
  },
  clinic: {
    label: "Клиника / Медцентр",
    callsPerDay: 90,
    chatsPerDay: 60,
    avgCallMinutes: 3.5,
    operatorSalary: 65000,
    operatorsCount: 3,
    automationTarget: 65,
  },
  ecommerce: {
    label: "E-commerce / Магазин",
    callsPerDay: 60,
    chatsPerDay: 200,
    avgCallMinutes: 3,
    operatorSalary: 50000,
    operatorsCount: 5,
    automationTarget: 70,
  },
  delivery: {
    label: "Служба доставки",
    callsPerDay: 200,
    chatsPerDay: 100,
    avgCallMinutes: 1.5,
    operatorSalary: 45000,
    operatorsCount: 6,
    automationTarget: 80,
  },
  services: {
    label: "Сервисные услуги",
    callsPerDay: 50,
    chatsPerDay: 70,
    avgCallMinutes: 5,
    operatorSalary: 60000,
    operatorsCount: 3,
    automationTarget: 60,
  },
};

/* ── Constants ────────────────────────────────────────────────────── */
const CALLFORCE_COST_PER_DIALOG = 12; // ₽ перелимит
const CALLFORCE_PLAN_MONTHLY = 7990;
const WORKING_DAYS = 30;

/* ── Helpers ─────────────────────────────────────────────────────── */
function fmt(n: number) {
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(n);
}

function fmtMoney(n: number) {
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(n) + " ₽";
}

/* ── Component ─────────────────────────────────────────────────────── */
export default function ROICalculator() {
  const [industry, setIndustry] = useState<Industry>("restaurant");
  const [callsPerDay, setCallsPerDay] = useState(PRESETS.restaurant.callsPerDay);
  const [chatsPerDay, setChatsPerDay] = useState(PRESETS.restaurant.chatsPerDay);
  const [operatorSalary, setOperatorSalary] = useState(PRESETS.restaurant.operatorSalary);
  const [operatorsCount, setOperatorsCount] = useState(PRESETS.restaurant.operatorsCount);
  const [automationTarget, setAutomationTarget] = useState(PRESETS.restaurant.automationTarget);
  const [avgCallMinutes, setAvgCallMinutes] = useState(PRESETS.restaurant.avgCallMinutes);

  const applyPreset = (key: Industry) => {
    setIndustry(key);
    const p = PRESETS[key];
    setCallsPerDay(p.callsPerDay);
    setChatsPerDay(p.chatsPerDay);
    setOperatorSalary(p.operatorSalary);
    setOperatorsCount(p.operatorsCount);
    setAutomationTarget(p.automationTarget);
    setAvgCallMinutes(p.avgCallMinutes);
  };

  const calc = useMemo(() => {
    const totalDialogs = (callsPerDay + chatsPerDay) * WORKING_DAYS;
    const autoDialogs = Math.round(totalDialogs * (automationTarget / 100));
    const humanDialogs = totalDialogs - autoDialogs;

    // Current cost: full operator team handles ALL dialogs
    const totalSalaryMonthly = operatorSalary * operatorsCount * 1.35; // +35% taxes/benefits
    const costPerOperatorMinute = totalSalaryMonthly / (operatorsCount * 21 * 8 * 60); // effective work minutes/month
    const totalHumanMinutes = callsPerDay * avgCallMinutes * WORKING_DAYS + chatsPerDay * 1.5 * WORKING_DAYS;
    const currentOpsCostForDialogs = totalHumanMinutes * costPerOperatorMinute;

    // With CallForce: human operators handle fewer dialogs
    const humanMinutesAfter = Math.round(totalHumanMinutes * (1 - automationTarget / 100));
    const opsCostAfter = humanMinutesAfter * costPerOperatorMinute;

    // CallForce subscription + overage
    const basePlanCost = CALLFORCE_PLAN_MONTHLY;
    const overageDialogs = Math.max(0, totalDialogs - 1000);
    const overageCost = overageDialogs * CALLFORCE_COST_PER_DIALOG;
    const callforceTotalCost = basePlanCost + overageCost;

    const totalBefore = currentOpsCostForDialogs;
    const totalAfter = opsCostAfter + callforceTotalCost;
    const savings = totalBefore - totalAfter;
    const savingsPercent = totalBefore > 0 ? (savings / totalBefore) * 100 : 0;
    const roiMonths = savings > 0 ? CALLFORCE_PLAN_MONTHLY / savings : Infinity;
    const freedOperators = Math.max(0, Math.round(operatorsCount * (automationTarget / 100) * 0.7));
    const timeSavedHours = (humanMinutesAfter > 0 ? totalHumanMinutes - humanMinutesAfter : 0) / 60;

    return {
      totalDialogs,
      autoDialogs,
      humanDialogs,
      totalBefore,
      totalAfter,
      savings,
      savingsPercent,
      roiMonths,
      callforceTotalCost,
      basePlanCost,
      overageCost,
      freedOperators,
      timeSavedHours,
      opsCostAfter,
      currentOpsCostForDialogs,
    };
  }, [callsPerDay, chatsPerDay, operatorSalary, operatorsCount, automationTarget, avgCallMinutes]);

  const barData = [
    { name: "Сейчас (операторы)", value: Math.round(calc.totalBefore / 1000) },
    { name: "С CallForce", value: Math.round(calc.totalAfter / 1000) },
  ];



  return (
    <main className="min-h-screen relative overflow-hidden bg-black selection:bg-zinc-800">
      {/* Background glow */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden flex items-center justify-center">
        <div className="absolute top-[-20%] right-[-10%] w-[600px] h-[600px] bg-emerald-900/20 rounded-full blur-[120px] opacity-40 animate-pulse"></div>
        <div className="absolute bottom-[-20%] left-[-10%] w-[500px] h-[500px] bg-zinc-900 rounded-full blur-[120px] opacity-40"></div>
      </div>

      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-white/5 bg-black/40 backdrop-blur-xl">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-white text-black flex items-center justify-center font-bold text-sm tracking-tighter">
              CF
            </div>
            <span className="font-bold text-lg tracking-tight text-white">CallForce</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors hidden sm:block">
              Главная
            </Link>
            <Link href="/register" className="text-sm font-medium bg-white text-black px-4 py-2 rounded-md hover:bg-zinc-200 transition-colors">
              Начать бесплатно
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative z-10 container mx-auto px-6 pt-16 pb-12 md:pt-24 md:pb-16">
        <MotionDiv className="max-w-3xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/10 bg-white/5 text-xs font-medium text-zinc-300 mb-6 backdrop-blur-md">
            <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
            Калькулятор окупаемости
          </div>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tighter text-white mb-6 leading-[1.1]">
            Сколько вы <span className="text-emerald-400">сэкономите</span> с CallForce?
          </h1>
          <p className="text-lg text-zinc-400 mb-2 max-w-2xl mx-auto leading-relaxed">
            Введите параметры вашего бизнеса и узнайте, насколько быстрее окупятся ИИ-агенты по сравнению с наймом операторов.
          </p>
          <p className="text-sm text-zinc-500">
            Расчёт основан на реальных данных: зарплаты, налоги, перелимит, тариф Business (7 990 ₽/мес).
          </p>
        </MotionDiv>
      </section>

      {/* Main layout: inputs + results */}
      <section className="relative z-10 container mx-auto px-6 pb-24">
        <div className="grid lg:grid-cols-5 gap-8 max-w-7xl mx-auto">

          {/* LEFT: Input panel (2 cols) */}
          <MotionDiv className="lg:col-span-2 p-6 rounded-2xl border border-white/5 bg-zinc-900/50 backdrop-blur-xl">
            <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
              <Calculator className="w-5 h-5 text-emerald-500" /> Параметры бизнеса
            </h2>

            {/* Industry presets */}
            <div className="mb-6">
              <label className="block text-sm text-zinc-400 mb-2">Отрасль (шаблон)</label>
              <div className="grid grid-cols-2 gap-2">
                {(Object.entries(PRESETS) as [Industry, typeof PRESETS.restaurant][]).map(([key, p]) => (
                  <button
                    key={key}
                    onClick={() => applyPreset(key)}
                    className={`text-left text-sm px-3 py-2 rounded-lg border transition-colors ${
                      industry === key
                        ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-300"
                        : "border-white/5 bg-white/[0.02] text-zinc-400 hover:bg-white/5 hover:text-white"
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Sliders */}
            <div className="space-y-5">
              <SliderInput
                label="Входящих звонков / день"
                value={callsPerDay}
                onChange={setCallsPerDay}
                min={10}
                max={500}
                step={10}
                icon={<Phone className="w-4 h-4" />}
              />
              <SliderInput
                label="Чатов / день (TG, WhatsApp, VK)"
                value={chatsPerDay}
                onChange={setChatsPerDay}
                min={10}
                max={500}
                step={10}
                icon={<MessageSquare className="w-4 h-4" />}
              />
              <SliderInput
                label="Средняя длительность звонка (мин)"
                value={avgCallMinutes}
                onChange={setAvgCallMinutes}
                min={0.5}
                max={10}
                step={0.5}
                format={(v) => `${v} мин`}
                icon={<Clock className="w-4 h-4" />}
              />
              <SliderInput
                label="Зарплата оператора (₽/мес на руки)"
                value={operatorSalary}
                onChange={setOperatorSalary}
                min={30000}
                max={120000}
                step={5000}
                format={(v) => fmtMoney(v)}
                icon={<Users className="w-4 h-4" />}
              />
              <SliderInput
                label="Кол-во операторов"
                value={operatorsCount}
                onChange={setOperatorsCount}
                min={1}
                max={20}
                step={1}
                format={(v) => `${v} чел.`}
              />
              <SliderInput
                label="Целевой % автоматизации"
                value={automationTarget}
                onChange={setAutomationTarget}
                min={30}
                max={95}
                step={5}
                format={(v) => `${v}%`}
              />
            </div>
          </MotionDiv>

          {/* RIGHT: Results panel (3 cols) */}
          <MotionDiv className="lg:col-span-3 space-y-6" delay={0.1}>
            {/* KPI cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KPICard
                label="Экономия / мес"
                value={fmtMoney(calc.savings)}
                accent={calc.savings > 0 ? "text-emerald-400" : "text-red-400"}
              />
              <KPICard
                label="Экономия"
                value={`${calc.savingsPercent.toFixed(0)}%`}
                accent="text-emerald-400"
              />
              <KPICard
                label="Окупаемость"
                value={calc.roiMonths !== Infinity ? `${calc.roiMonths.toFixed(1)} мес` : ">12 мес"}
                accent="text-amber-400"
              />
              <KPICard
                label="Освобождено операторов"
                value={`${calc.freedOperators} чел.`}
                accent="text-blue-400"
              />
            </div>

            {/* Before / After chart */}
            <div className="p-6 rounded-2xl border border-white/5 bg-zinc-900/50 backdrop-blur-xl">
              <h3 className="text-base font-semibold text-white mb-4">Затраты на обработку диалогов (тыс. ₽/мес)</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={barData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                    <XAxis dataKey="name" tick={{ fill: "#a1a1aa", fontSize: 12 }} axisLine={{ stroke: "#3f3f46" }} />
                    <YAxis tick={{ fill: "#a1a1aa", fontSize: 12 }} axisLine={{ stroke: "#3f3f46" }} tickFormatter={(v) => `${v}K`} />
                    <Tooltip
                      contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: 8, color: "#fff" }}
                      formatter={(value) => [`${fmt(Number(value ?? 0) * 1000)} ₽`, ""]}
                    />
                    <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                      <Cell fill="#ef4444" />
                      <Cell fill="#10b981" />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Cost breakdown */}
            <div className="p-6 rounded-2xl border border-white/5 bg-zinc-900/50 backdrop-blur-xl">
              <h3 className="text-base font-semibold text-white mb-4">Детализация затрат с CallForce</h3>
              <div className="space-y-3">
                <CostRow label="Операторы (после автоматизации)" value={fmtMoney(calc.opsCostAfter)} />
                <CostRow label="Тариф Business" value={fmtMoney(calc.basePlanCost)} />
                {calc.overageCost > 0 && (
                  <CostRow label={`Перелимит (${fmt(calc.totalDialogs - 1000)} × ${CALLFORCE_COST_PER_DIALOG} ₽)`} value={fmtMoney(calc.overageCost)} />
                )}
                <div className="border-t border-white/10 pt-3 flex justify-between text-white font-semibold">
                  <span>Итого с CallForce</span>
                  <span>{fmtMoney(calc.totalAfter)}/мес</span>
                </div>
                <div className="flex justify-between text-emerald-400 font-bold text-lg pt-1">
                  <span>Экономия</span>
                  <span>{fmtMoney(calc.savings)}/мес</span>
                </div>
                <div className="flex justify-between text-zinc-400 text-sm">
                  <span>Экономия за год</span>
                  <span className="text-emerald-300">{fmtMoney(calc.savings * 12)}</span>
                </div>
                <div className="flex justify-between text-zinc-400 text-sm">
                  <span>Сэкономлено часов работы операторов</span>
                  <span>{fmt(Math.round(calc.timeSavedHours))} ч/мес</span>
                </div>
              </div>
            </div>

            {/* CTA */}
            <div className="p-6 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 text-center">
              <h3 className="text-lg font-bold text-white mb-2">
                Готовы сэкономить {fmtMoney(calc.savings)}/мес?
              </h3>
              <p className="text-sm text-zinc-400 mb-6">
                Подключите CallForce за 10 минут. Первый месяц — бесплатно.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Link
                  href="/register"
                  className="inline-flex items-center justify-center gap-2 bg-white text-black px-6 py-3 rounded-lg font-medium hover:bg-zinc-200 transition-colors"
                >
                  Начать бесплатно <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  href="/"
                  className="inline-flex items-center justify-center gap-2 border border-white/10 text-white px-6 py-3 rounded-lg font-medium hover:bg-white/5 transition-colors"
                >
                  Вернуться на сайт
                </Link>
              </div>
            </div>
          </MotionDiv>
        </div>
      </section>
    </main>
  );
}

/* ── Sub-components ─────────────────────────────────────────────── */

function SliderInput({
  label,
  value,
  onChange,
  min,
  max,
  step,
  format,
  icon,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step: number;
  format?: (v: number) => string;
  icon?: React.ReactNode;
}) {
  const display = format ? format(value) : fmt(value);
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-sm text-zinc-400 flex items-center gap-1.5">{icon}{label}</label>
        <span className="text-sm font-mono text-white bg-zinc-800 px-2 py-0.5 rounded">{display}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-2 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
      />
    </div>
  );
}

function KPICard({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className="p-4 rounded-xl border border-white/5 bg-zinc-900/50">
      <div className="text-xs text-zinc-500 mb-1">{label}</div>
      <div className={`text-xl font-bold ${accent}`}>{value}</div>
    </div>
  );
}

function CostRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-zinc-400">{label}</span>
      <span className="text-zinc-300">{value}/мес</span>
    </div>
  );
}
