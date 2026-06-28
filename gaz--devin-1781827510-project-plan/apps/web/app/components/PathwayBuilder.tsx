"use client";

import React, { useCallback, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  type Node,
  type Edge,
  type Connection,
  type NodeChange,
  type EdgeChange,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Save, ArrowLeft, Plus } from "lucide-react";
import Link from "next/link";
import { saveAgentPathwayAction } from "../actions";
import { toast } from "sonner";

const nodeTypesConfig = [
  { type: "start", label: "Start", color: "bg-emerald-500" },
  { type: "say", label: "Say", color: "bg-blue-500" },
  { type: "ask", label: "Ask", color: "bg-amber-500" },
  { type: "condition", label: "Condition", color: "bg-purple-500" },
  { type: "knowledge", label: "Knowledge", color: "bg-indigo-500" },
  { type: "tool", label: "Tool", color: "bg-pink-500" },
  { type: "transfer", label: "Transfer", color: "bg-red-500" },
  { type: "end", label: "End", color: "bg-zinc-500" },
];

export function PathwayBuilder({
  agentId,
  agentName,
  initialNodes = [],
  initialEdges = [],
}: {
  agentId: string;
  agentName: string;
  initialNodes?: Node[];
  initialEdges?: Edge[];
}) {
  const [nodes, setNodes] = useState<Node[]>(initialNodes.length ? initialNodes : [{ id: "start-1", type: "default", position: { x: 250, y: 50 }, data: { label: "Start", type: "start" } }]);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [isSaving, setIsSaving] = useState(false);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    []
  );

  const addNode = (type: string, label: string) => {
    const newNode = {
      id: `${type}-${Date.now()}`,
      position: { x: Math.random() * 200 + 100, y: Math.random() * 200 + 100 },
      data: { label, type },
    };
    setNodes((nds) => [...nds, newNode]);
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      const res = await saveAgentPathwayAction(agentId, nodes, edges);
      if (res.success) {
        toast.success("Сценарий сохранён успешно");
      } else {
        toast.error(`Ошибка: ${res.error}`);
      }
    } catch {
      toast.error("Ошибка при сохранении");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      <header className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-white/5 bg-zinc-950/50 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <Link
            href={`/agents/${agentId}`}
            className="flex items-center gap-2 text-sm font-medium text-zinc-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Назад к агенту
          </Link>
          <div className="h-4 w-px bg-white/10" />
          <h1 className="text-lg font-semibold text-white">
            Конструктор сценария: <span className="text-emerald-400">{agentName}</span>
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center gap-2 bg-purple-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple-500 transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {isSaving ? "Сохранение..." : "Сохранить сценарий"}
          </button>
        </div>
      </header>

      <div className="flex flex-1 min-h-0 relative">
        <div className="w-64 flex-shrink-0 border-r border-white/5 bg-zinc-900/50 p-4 overflow-y-auto z-10">
          <h2 className="text-xs font-mono text-zinc-500 mb-4 uppercase tracking-wider">
            Палитра узлов
          </h2>
          <div className="grid grid-cols-1 gap-2">
            {nodeTypesConfig.map((conf) => (
              <button
                key={conf.type}
                onClick={() => addNode(conf.type, conf.label)}
                className="flex items-center gap-3 p-3 rounded-lg border border-white/5 bg-black hover:border-white/20 transition-colors text-left"
              >
                <div className={`w-3 h-3 rounded-full ${conf.color}`} />
                <span className="text-sm font-medium text-zinc-300">{conf.label}</span>
                <Plus className="w-4 h-4 text-zinc-600 ml-auto" />
              </button>
            ))}
          </div>
          
          <div className="mt-8 p-4 rounded-xl border border-white/5 bg-black/50">
            <p className="text-xs text-zinc-400 leading-relaxed">
              Добавляйте узлы на холст и соединяйте их линиями для создания диалогового сценария. Обязательно должен быть один узел Start.
            </p>
          </div>
        </div>

        <div className="flex-1 relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            fitView
            colorMode="dark"
            className="bg-black"
          >
            <Background color="#3f3f46" gap={16} />
            <Controls className="bg-zinc-900 border-white/10 fill-white" />
            <MiniMap 
              nodeColor={(n) => {
                const conf = nodeTypesConfig.find(c => c.type === n.data?.type);
                return conf ? conf.color.replace('bg-', '') : '#3f3f46';
              }}
              maskColor="rgba(0, 0, 0, 0.7)"
              className="bg-zinc-900 border border-white/10 rounded-xl overflow-hidden shadow-xl"
            />
          </ReactFlow>
        </div>
      </div>
    </div>
  );
}
