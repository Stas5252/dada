import { DashboardShell } from "../components/DashboardShell";
import { ResultNotice } from "../components/ResultNotice";
import { getConversations } from "../../lib/mvp-data";
import { ConversationsList } from "../components/ConversationsList";

export default async function ConversationsPage() {
  const conversationsResult = await getConversations();

  return (
    <DashboardShell
      activePath="/conversations"
      eyebrow="Диалоги"
      title="История диалогов"
      description="Фильтры, transcript, tools, sources и summary для каждого разговора с клиентом."
    >
      <div className="space-y-6">
        <ResultNotice result={conversationsResult} />
        <ConversationsList initialConversations={conversationsResult.data} />
      </div>
    </DashboardShell>
  );
}
