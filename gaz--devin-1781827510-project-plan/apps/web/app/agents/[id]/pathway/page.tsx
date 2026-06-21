"use client";

import { useCallback } from "react";
import { ReactFlow, MiniMap, Controls, Background, useNodesState, useEdgesState, addEdge, type Connection } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { ArrowLeft, Save } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { useParams } from "next/navigation";

const initialNodes = [
  { id: "1", position: { x: 250, y: 50 }, data: { label: "Начало (Входящий звонок)" }, type: "input" },
  { id: "2", position: { x: 250, y: 150 }, data: { label: "Приветствие: Здравствуйте, это пиццерия!" } },
  { id: "3", position: { x: 100, y: 250 }, data: { label: "Спросить про меню" } },
  { id: "4", position: { x: 400, y: 250 }, data: { label: "Оформить заказ" } },
  { id: "5", position: { x: 100, y: 350 }, data: { label: "RAG: Поиск по Knowledge Base" } },
  { id: "6", position: { x: 400, y: 350 }, data: { label: "Tool: create_delivery_order" }, type: "output" },
];

const initialEdges = [
  { id: "e1-2", source: "1", target: "2", animated: true },
  { id: "e2-3", source: "2", target: "3", label: "Интент: Вопрос" },
  { id: "e2-4", source: "2", target: "4", label: "Интент: Заказ" },
  { id: "e3-5", source: "3", target: "5" },
  { id: "e4-6", source: "4", target: "6" },
];

export default function PathwayEditorPage() {
  const { id } = useParams();
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback((params: Connection) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

  const handleSave = () => {
    toast.success("Граф сценария успешно сохранен (Mock)!");
  };

  return (
    <div className="flex flex-col h-full bg-black text-white relative">
      <div className="flex items-center justify-between p-4 border-b border-white/10 bg-zinc-950">
        <div className="flex items-center gap-4">
          <Link href={`/agents/${id}`} className="text-zinc-400 hover:text-white transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="text-xl font-semibold">Pathway Editor</h1>
          <span className="px-2 py-1 bg-violet-500/10 text-violet-400 border border-violet-500/20 text-xs rounded-md">
            Visual Builder (Beta)
          </span>
        </div>
        <button
          onClick={handleSave}
          className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm transition-colors"
        >
          <Save className="w-4 h-4" /> Сохранить
        </button>
      </div>

      <div className="flex-1 w-full h-full relative" style={{ minHeight: "calc(100vh - 73px)" }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          fitView
          className="bg-black"
          colorMode="dark"
        >
          <Controls className="bg-zinc-900 border-zinc-800 fill-white" />
          <MiniMap className="bg-zinc-900 border-zinc-800" maskColor="rgba(0,0,0,0.5)" nodeColor="#3f3f46" />
          <Background color="#27272a" gap={16} />
        </ReactFlow>
      </div>
    </div>
  );
}
