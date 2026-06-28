import { getAgent } from "../../../../lib/mvp-data";
import { getAgentPathway } from "../../../../lib/mvp-data";
import { PathwayBuilder } from "../../../components/PathwayBuilder";
import { DashboardShell } from "../../../components/DashboardShell";
import { EmptyState } from "../../../components/EmptyState";
import { type Node, type Edge } from "@xyflow/react";

type AgentPathwayPageProps = {
  params: Promise<{
    id: string;
  }>;
};

export default async function AgentPathwayPage({ params }: AgentPathwayPageProps) {
  const { id } = await params;
  
  const [agentResult, pathwayResult] = await Promise.all([
    getAgent(id),
    getAgentPathway(id),
  ]);

  const agent = agentResult.data;
  const pathway = pathwayResult.data;

  if (!agent) {
    return (
      <DashboardShell
        activePath="/agents"
        eyebrow="Agent Builder"
        title="Агент не найден"
      >
        <EmptyState
          actionHref="/agents"
          actionLabel="Вернуться к агентам"
          description="Агент не найден или у вас нет к нему доступа."
          title="Ошибка"
        />
      </DashboardShell>
    );
  }

  const initialNodes = (pathway?.nodes as unknown as Node[]) || [];
  const initialEdges = (pathway?.edges as unknown as Edge[]) || [];

  return (
    <div className="bg-black min-h-screen text-white">
      {/* We skip DashboardShell here to give the builder full screen real estate, 
          but PathwayBuilder itself has a header. */}
      <PathwayBuilder 
        agentId={agent.id} 
        agentName={agent.name} 
        initialNodes={initialNodes}
        initialEdges={initialEdges}
      />
    </div>
  );
}
