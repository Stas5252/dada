import { CreditCard, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { getCoreTenantId } from "../../../lib/core-api";
import { redirect } from "next/navigation";

type CheckoutProps = {
  searchParams?: Promise<{
    plan?: string;
  }>;
};

export default async function CheckoutPage({ searchParams }: CheckoutProps) {
  const resolvedSearchParams = await searchParams;
  const plan = (resolvedSearchParams?.plan || "start").toLowerCase();
  const tenantId = await getCoreTenantId();
  
  const planDetails = {
    start: { name: "Start Plan", price: 2990, value: "2990.00" },
    business: { name: "Business Plan", price: 7990, value: "7990.00" },
    pro: { name: "Pro Plan", price: 19990, value: "19990.00" },
    enterprise: { name: "Enterprise Plan", price: 49990, value: "49990.00" },
  }[plan] || { name: "Start Plan", price: 2990, value: "2990.00" };

  async function processPaymentAction() {
    "use server";
    
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
    const appUrl = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

    try {
      // 1. Try real checkout API
      const checkoutRes = await fetch(`${apiUrl}/api/v1/billing/checkout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-tenant-id": tenantId,
        },
        body: JSON.stringify({
          plan: plan,
          return_url: `${appUrl}/billing?notice=payment-success`,
        }),
      });

      if (checkoutRes.ok) {
        const checkoutData = await checkoutRes.json();
        // If real YooKassa is configured, it returns a confirmation_url
        if (checkoutData.confirmation_url) {
          redirect(checkoutData.confirmation_url);
        }
      }
      
      // 2. Fallback to Simulation if YooKassa is not configured
      const webhookPayload = {
        type: "notification",
        event: "payment.succeeded",
        object: {
          id: `sim-${Math.random().toString(36).substr(2, 9)}`,
          status: "succeeded",
          amount: {
            value: planDetails.value,
            currency: "RUB",
          },
          metadata: {
            tenant_id: tenantId,
            plan_name: plan,
          },
        },
      };

      const response = await fetch(`${apiUrl}/api/v1/billing/yookassa/webhook`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(webhookPayload),
      });

      if (response.ok) {
        redirect("/billing?notice=payment-success");
      } else {
        redirect("/billing?notice=payment-failed");
      }
    } catch (e) {
      // Next.js redirect throws a specific error, we must rethrow it
      if (e instanceof Error && e.message === "NEXT_REDIRECT") {
        throw e;
      }
      console.error("Payment error", e);
      redirect("/billing?notice=payment-failed");
    }
  }

  return (
    <main className="min-h-screen bg-black text-white flex items-center justify-center p-6 relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden flex items-center justify-center">
        <div className="w-[400px] h-[400px] bg-purple-500 rounded-full blur-[140px] opacity-20 animate-pulse"></div>
      </div>

      <div className="relative z-10 w-full max-w-md bg-zinc-900/60 border border-white/10 rounded-2xl p-6 shadow-2xl backdrop-blur-2xl">
        <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-6">
          <Link href="/billing" className="text-zinc-400 hover:text-white transition-colors flex items-center gap-1.5 text-sm">
            <ArrowLeft className="w-4 h-4" /> Назад в биллинг
          </Link>
          <span className="text-xs text-zinc-500 font-mono">yookassa.ru simulation</span>
        </div>

        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-purple-500/10 border border-purple-500/20 text-purple-400 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <CreditCard className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold text-white">Шлюз оплаты ЮKassa</h1>
          <p className="text-sm text-zinc-400 mt-1">Оплата подписки на платформу CallForce</p>
        </div>

        <div className="bg-black/40 border border-white/5 rounded-xl p-4 mb-6 space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-zinc-400">Услуга:</span>
            <span className="font-semibold text-white">Подписка: {planDetails.name}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-zinc-400">Тенант ID:</span>
            <span className="font-mono text-xs text-zinc-300">{tenantId.slice(0, 8)}...{tenantId.slice(-8)}</span>
          </div>
          <div className="border-t border-white/5 pt-3 flex justify-between text-base">
            <span className="text-zinc-300 font-medium">К оплате:</span>
            <span className="font-bold text-emerald-400">{planDetails.price.toLocaleString()} ₽</span>
          </div>
        </div>

        <form action={processPaymentAction} className="space-y-3">
          <button
            type="submit"
            className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-semibold shadow-lg shadow-emerald-600/15 transition-all text-sm"
          >
            Оплатить и подтвердить платеж
          </button>
          
          <Link
            href="/billing?notice=payment-cancelled"
            className="block w-full py-3 text-center bg-transparent border border-white/10 hover:bg-white/5 text-zinc-400 hover:text-white rounded-xl font-medium transition-all text-sm"
          >
            Отменить операцию
          </Link>
        </form>
      </div>
    </main>
  );
}
