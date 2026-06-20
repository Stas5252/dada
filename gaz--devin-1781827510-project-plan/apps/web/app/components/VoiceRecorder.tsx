"use client";

import { useState, useRef, useEffect } from "react";
import { Mic, Square, Play, Loader2, Info, MessageSquare } from "lucide-react";

type VoiceRecorderProps = {
  agentId: string;
  tenantId: string;
};

export function VoiceRecorder({ agentId, tenantId }: VoiceRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<string | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [sttText, setSttText] = useState<string | null>(null);
  const [llmText, setLlmText] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const binaryChunksRef = useRef<Blob[]>([]);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const startRecording = async () => {
    try {
      setAudioUrl(null);
      setSttText(null);
      setLlmText(null);
      setProcessingStatus(null);
      binaryChunksRef.current = [];

      // 1. Initialize WebSocket connection
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";
      const wsProtocol = apiBaseUrl.startsWith("https") ? "wss" : "ws";
      const wsBaseUrl = apiBaseUrl.replace(/^https?:\/\//, "");
      const wsUrl = `${wsProtocol}://${wsBaseUrl}/api/v1/voice/stream/${agentId}?tenant_id=${tenantId}`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.binaryType = "blob";

      ws.onopen = () => {
        console.log("WebSocket voice stream connected");
      };

      ws.onerror = (err) => {
        console.error("WebSocket stream error", err);
      };

      ws.onclose = () => {
        console.log("WebSocket voice stream closed");
      };

      ws.onmessage = async (event) => {
        if (typeof event.data === "string") {
          try {
            const msg = JSON.parse(event.data);
            if (msg.event === "stt") {
              setSttText(msg.text);
              setProcessingStatus("ИИ обдумывает ответ...");
            } else if (msg.event === "llm") {
              setLlmText(msg.text);
              setProcessingStatus("Синтезируем голосовой ответ...");
            } else if (msg.event === "done") {
              setIsProcessing(false);
              setProcessingStatus(null);
              if (binaryChunksRef.current.length > 0) {
                const responseBlob = new Blob(binaryChunksRef.current, { type: "audio/mpeg" });
                const url = URL.createObjectURL(responseBlob);
                setAudioUrl(url);
              }
              ws.close();
            } else if (msg.event === "error") {
              setIsProcessing(false);
              setProcessingStatus(null);
              alert(`Ошибка: ${msg.message}`);
              ws.close();
            }
          } catch (err) {
            console.error("Failed to parse websocket message", err);
          }
        } else if (event.data instanceof Blob) {
          binaryChunksRef.current.push(event.data);
        }
      };

      // 2. Access microphone and start recording in 200ms slices
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      let options = {};
      if (MediaRecorder.isTypeSupported("audio/webm")) {
        options = { mimeType: "audio/webm" };
      }

      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
          ws.send(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start(200);
      setIsRecording(true);
    } catch (err) {
      console.error("Failed to start recording", err);
      alert("Не удалось получить доступ к микрофону или установить WebSocket-соединение с сервером");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsProcessing(true);
      setProcessingStatus("Распознаем речь...");

      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send("stop_record");
      }
    }
  };

  return (
    <div className="bg-black border border-white/10 p-6 rounded-xl flex flex-col items-center justify-center space-y-6 w-full max-w-xl mx-auto">
      <div className="text-center">
        <h3 className="text-lg font-medium text-white mb-2">Голосовой канал (WebSocket Real-time)</h3>
        <p className="text-sm text-zinc-400">
          Нажмите на микрофон и говорите. Ваше аудио транслируется на сервер в реальном времени.
        </p>
      </div>

      <div className="flex items-center justify-center gap-4">
        {!isRecording ? (
          <button
            onClick={startRecording}
            disabled={isProcessing}
            className="w-16 h-16 rounded-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center transition-colors"
          >
            {isProcessing ? (
              <Loader2 className="w-6 h-6 text-black animate-spin" />
            ) : (
              <Mic className="w-6 h-6 text-black" />
            )}
          </button>
        ) : (
          <button
            onClick={stopRecording}
            className="w-16 h-16 rounded-full bg-red-500 hover:bg-red-400 flex items-center justify-center transition-colors animate-pulse"
          >
            <Square className="w-6 h-6 text-white fill-current" />
          </button>
        )}
      </div>

      {isRecording && (
        <div className="flex items-center gap-2 text-sm text-red-400 font-medium animate-pulse">
          <div className="w-2 h-2 rounded-full bg-red-500" />
          Идет запись и стриминг...
        </div>
      )}

      {isProcessing && (
        <div className="flex items-center gap-2 text-sm text-emerald-400 font-medium bg-emerald-950/20 px-4 py-2 rounded-lg border border-emerald-500/10">
          <Loader2 className="w-4 h-4 animate-spin" />
          {processingStatus || "Обработка..."}
        </div>
      )}

      {/* Real-time dialogue details */}
      {(sttText || llmText) && (
        <div className="w-full space-y-3 bg-zinc-900/40 p-4 rounded-xl border border-white/5">
          {sttText && (
            <div className="space-y-1">
              <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider block">Вы сказали:</span>
              <p className="text-sm text-zinc-300 italic">&quot;{sttText}&quot;</p>
            </div>
          )}
          {llmText && (
            <div className="space-y-1 border-t border-white/5 pt-2">
              <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider block flex items-center gap-1">
                <MessageSquare className="w-3 h-3 text-emerald-400" />
                Ответ ИИ:
              </span>
              <p className="text-sm text-white font-medium">{llmText}</p>
            </div>
          )}
        </div>
      )}

      {audioUrl && (
        <div className="w-full bg-zinc-900 rounded-lg p-4 flex flex-col gap-3">
          <div className="flex items-center gap-2 text-sm text-white font-medium">
            <Play className="w-4 h-4 text-emerald-400" />
            Прослушать аудио ответ:
          </div>
          <audio src={audioUrl} controls autoPlay className="w-full h-10" />
        </div>
      )}

      <div className="mt-4 flex items-start gap-3 p-3 bg-white/5 rounded-lg border border-white/5 w-full">
         <Info className="w-5 h-5 text-zinc-400 flex-shrink-0" />
         <p className="text-xs text-zinc-400 leading-relaxed">
           Этот плеер использует <b>WebSocket-стриминг</b>. Запись транслируется пакетами по 200ms, а аудио-ответ генерируется с минимальной задержкой. При отсутствии OpenAI API ключей бот симулирует заказ пиццы.
         </p>
      </div>
    </div>
  );
}
