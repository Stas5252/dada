import { getConversations } from "../../lib/mvp-data";
import { OperatorConsoleContainer } from "./OperatorConsoleContainer";

export const metadata = {
  title: "Operator Console - CallForce",
};

export default async function OperatorConsolePage() {
  const result = await getConversations();
  const conversations = result.state === "live" ? result.data : [];

  // Filter for active conversations
  const activeConversations = conversations.filter(
    (c) => c.status === "open" || c.status === "escalated"
  );

  // Fallback mock data if not live or empty
  const displayConversations = activeConversations.length > 0 ? activeConversations : [
    {
      id: "conv-1002",
      channel: "SIP" as const,
      customer: "Номер +7 *** 21-45",
      status: "escalated" as const,
      summary: "Клиент просил изменить состав заказа после передачи на кухню.",
      latency: "1.4с",
      updatedAt: "28 минут назад",
    },
    {
      id: "conv-1003",
      channel: "Widget" as const,
      customer: "Гость сайта",
      status: "open" as const,
      summary: "Вопрос о сертификатах не найден в базе знаний.",
      latency: "1.1с",
      updatedAt: "1 час назад",
    }
  ];

  return <OperatorConsoleContainer initialConversations={displayConversations} />;
}
