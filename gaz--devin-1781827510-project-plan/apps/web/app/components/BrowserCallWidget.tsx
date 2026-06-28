/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useState, useEffect, useRef } from "react";
import { Phone, PhoneOff, Mic, MicOff, Volume2, Send, X } from "lucide-react";
import { sendVoicePreviewMessageAction } from "../actions";
import { toast } from "sonner";

type BrowserCallWidgetProps = {
  agentId: string;
  agentName?: string;
  buttonClassName?: string;
  buttonText?: string;
};

type Message = {
  sender: "bot" | "user" | "system";
  text: string;
  time: string;
};

export function BrowserCallWidget({
  agentId,
  agentName = "ИИ-Ассистент",
  buttonClassName = "",
  buttonText = "Позвонить в браузере (Симулятор)",
}: BrowserCallWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [callState, setCallState] = useState<"idle" | "dialing" | "connected" | "ended">("idle");
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false); // Whether bot is currently speaking
  const [isListening, setIsListening] = useState(false); // Whether mic is active
  const [recognitionActive, setRecognitionActive] = useState(false);

  const sessionIdRef = useRef<string>("");
  const audioContextRef = useRef<AudioContext | null>(null);
  const oscillatorRef = useRef<OscillatorNode | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const recognitionRef = useRef<any>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Generate random session ID
  const startNewSession = () => {
    sessionIdRef.current = `browser-call-${Math.random().toString(36).substring(2, 11)}`;
  };

  // 1. Web Audio API - Telephone Dial Tones Simulator
  const startDialTone = () => {
    try {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioContextClass) return;

      const ctx = new AudioContextClass();
      audioContextRef.current = ctx;

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sine";
      // 425 Hz is standard Russian telephone line ring frequency
      osc.frequency.setValueAtTime(425, ctx.currentTime);

      gain.gain.setValueAtTime(0, ctx.currentTime);

      osc.connect(gain);
      gain.connect(ctx.destination);

      oscillatorRef.current = osc;
      gainNodeRef.current = gain;

      osc.start(0);

      // Pulse dial tone: 1 second beep, 3 seconds silence
      let active = false;
      const playTone = () => {
        if (ctx.state === "closed" || callState !== "dialing") return;
        active = !active;
        if (active) {
          gain.gain.linearRampToValueAtTime(0.15, ctx.currentTime + 0.05);
          // Auto stop beep after 1 sec
          setTimeout(() => {
            if (ctx.state !== "closed" && gainNodeRef.current) {
              gain.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.05);
            }
          }, 1000);
        }
      };

      playTone(); // start immediately
      const interval = setInterval(playTone, 4000);

      // Cleanup on state change
      (osc as any).dialToneInterval = interval;
    } catch (e) {
      console.error("Failed to start audio context for dial tone", e);
    }
  };

  const stopDialTone = () => {
    if (oscillatorRef.current) {
      if ((oscillatorRef.current as any).dialToneInterval) {
        clearInterval((oscillatorRef.current as any).dialToneInterval);
      }
      try {
        oscillatorRef.current.stop();
      } catch {}
      oscillatorRef.current.disconnect();
      oscillatorRef.current = null;
    }
    if (gainNodeRef.current) {
      gainNodeRef.current.disconnect();
      gainNodeRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
  };

  // 2. Web Speech API - Text-to-Speech (Bot voice synthesis)
  const speakText = (text: string, callback?: () => void) => {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      callback?.();
      return;
    }

    // Cancel active speech
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "ru-RU";

    // Try to find Russian voice
    const voices = window.speechSynthesis.getVoices();
    const ruVoice = voices.find((v) => v.lang.startsWith("ru"));
    if (ruVoice) {
      utterance.voice = ruVoice;
    }

    utterance.onstart = () => {
      setIsSpeaking(true);
      // Pause speech recognition while bot is speaking to prevent self-triggering
      if (recognitionRef.current && recognitionActive) {
        try {
          recognitionRef.current.abort();
        } catch {}
      }
    };

    utterance.onend = () => {
      setIsSpeaking(false);
      callback?.();
      // Resume speech recognition
      if (recognitionRef.current && recognitionActive && !isMuted) {
        try {
          recognitionRef.current.start();
        } catch {}
      }
    };

    utterance.onerror = (e) => {
      console.error("Speech synthesis error", e);
      setIsSpeaking(false);
      callback?.();
    };

    window.speechSynthesis.speak(utterance);
  };

  // 3. Web Speech API - Speech-to-Text (User microphone recognition)
  const setupSpeechRecognition = () => {
    const SpeechClass = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechClass) {
      toast.warning("Ваш браузер не поддерживает голосовой ввод. Вы можете общаться текстом.");
      return;
    }

    const rec = new SpeechClass();
    rec.continuous = true;
    rec.interimResults = false;
    rec.lang = "ru-RU";

    rec.onstart = () => {
      setIsListening(true);
    };

    rec.onend = () => {
      setIsListening(false);
      // Auto-restart if call is still active and not muted
      if (recognitionActive && !isMuted && callState === "connected" && !isSpeaking) {
        try {
          rec.start();
        } catch {}
      }
    };

    rec.onerror = (event: any) => {
      console.error("Speech recognition error", event);
      if (event.error === "not-allowed") {
        toast.error("Доступ к микрофону заблокирован. Разрешите микрофон в браузере.");
        setIsMuted(true);
        setRecognitionActive(false);
      }
    };

    rec.onresult = (event: any) => {
      const resultText = event.results[event.results.length - 1][0].transcript;
      if (resultText && resultText.trim()) {
        sendMessage(resultText.trim());
      }
    };

    recognitionRef.current = rec;
  };

  // 4. Waveform Canvas Animation
  const drawWaveform = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    let phase = 0;

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Determine waveform height based on status
      let amp = 5; // idle fluctuation
      if (callState === "dialing") {
        amp = 8 + Math.sin(Date.now() / 150) * 4;
      } else if (isSpeaking) {
        amp = 25 + Math.random() * 20; // speaking high amplitude
      } else if (isListening && !isMuted) {
        amp = 8 + Math.random() * 10; // listening low amplitude
      }

      ctx.lineWidth = 3;
      
      // Wave 1
      ctx.strokeStyle = "rgba(168, 85, 247, 0.4)"; // Purple
      ctx.beginPath();
      for (let x = 0; x < width; x++) {
        const y = height / 2 + Math.sin(x * 0.02 + phase) * amp;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Wave 2
      ctx.strokeStyle = "rgba(16, 185, 129, 0.6)"; // Emerald
      ctx.beginPath();
      for (let x = 0; x < width; x++) {
        const y = height / 2 + Math.sin(x * 0.015 - phase + 1) * (amp * 0.8);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      phase += 0.1;
      animationFrameRef.current = requestAnimationFrame(render);
    };

    render();
  };

  const stopWaveform = () => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
  };

  // Actions trigger
  const handleStartCall = () => {
    setIsOpen(true);
    setCallState("dialing");
    setMessages([{ sender: "system", text: "Набор номера агента...", time: getFormattedTime() }]);
    startNewSession();
    
    // Start dial beep simulation
    startDialTone();

    // Start visuals
    setTimeout(() => {
      drawWaveform();
    }, 100);

    // Simulated network delay for connecting
    setTimeout(async () => {
      stopDialTone();
      setCallState("connected");
      setMessages((prev) => [...prev, { sender: "system", text: "Соединение установлено", time: getFormattedTime() }]);
      
      // Trigger first message from agent (greeting)
      // We send "привет" (hello) to let Scenario Engine find the start node
      try {
        const res = await sendVoicePreviewMessageAction(agentId, "начало", sessionIdRef.current);
        if (res.success && res.response_text) {
          addMessage("bot", res.response_text);
          speakText(res.response_text);
        } else {
          const fallbackMsg = "Здравствуйте! Это голосовой ИИ-помощник CallForce. Я готов принять ваш заказ.";
          addMessage("bot", fallbackMsg);
          speakText(fallbackMsg);
        }
      } catch {
        const fallbackMsg = "Здравствуйте! Это голосовой ИИ-помощник. Чем я могу помочь?";
        addMessage("bot", fallbackMsg);
        speakText(fallbackMsg);
      }

      // Initialize microphone recognition
      setupSpeechRecognition();
      if (recognitionRef.current && !isMuted) {
        setRecognitionActive(true);
        try {
          recognitionRef.current.start();
        } catch {}
      }
    }, 3500);
  };

  const handleEndCall = () => {
    stopDialTone();
    stopWaveform();
    
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      recognitionRef.current = null;
    }
    setRecognitionActive(false);

    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }

    setCallState("ended");
    setMessages((prev) => [...prev, { sender: "system", text: "Звонок завершен", time: getFormattedTime() }]);
  };

  const toggleMute = () => {
    const nextMute = !isMuted;
    setIsMuted(nextMute);

    if (recognitionRef.current) {
      if (nextMute) {
        try {
          recognitionRef.current.stop();
        } catch {}
      } else {
        try {
          recognitionRef.current.start();
        } catch {}
      }
    }
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || callState !== "connected") return;

    addMessage("user", text);
    
    // Process response
    try {
      const res = await sendVoicePreviewMessageAction(agentId, text, sessionIdRef.current);
      if (res.success && res.response_text) {
        addMessage("bot", res.response_text);
        speakText(res.response_text);
      } else {
        const errorMsg = "Извините, возникли проблемы при связи с сервером.";
        addMessage("bot", errorMsg);
        speakText(errorMsg);
      }
    } catch {
      const errorMsg = "Извините, не удалось распознать сценарий.";
      addMessage("bot", errorMsg);
      speakText(errorMsg);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    sendMessage(inputText.trim());
    setInputText("");
  };

  const addMessage = (sender: "bot" | "user" | "system", text: string) => {
    setMessages((prev) => [...prev, { sender, text, time: getFormattedTime() }]);
  };

  const getFormattedTime = () => {
    const d = new Date();
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  };

  // Close widget layout
  const handleCloseOverlay = () => {
    handleEndCall();
    setIsOpen(false);
    setCallState("idle");
    setMessages([]);
  };

  // Ensure voices are loaded in browser
  useEffect(() => {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.getVoices();
    }
  }, []);

  return (
    <>
      <button
        onClick={handleStartCall}
        className={`flex items-center gap-2 justify-center px-4 py-2.5 rounded-lg border text-sm font-semibold transition-all hover:scale-[1.02] cursor-pointer ${
          buttonClassName || "bg-purple-600 border-purple-500 hover:bg-purple-500 text-white shadow-lg shadow-purple-600/20"
        }`}
      >
        <Phone className="w-4 h-4 animate-pulse" />
        {buttonText}
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-300 p-4">
          <div className="relative w-full max-w-lg bg-zinc-950 border border-white/10 rounded-2xl shadow-[0_0_50px_rgba(168,85,247,0.15)] flex flex-col h-[600px] overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-white/10 bg-zinc-900/50">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 font-bold text-sm">
                  CF
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">{agentName}</h3>
                  <span className="text-[10px] text-emerald-400 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                    {callState === "dialing" ? "Набор номера..." : callState === "connected" ? "Звонок активен" : "Звонок завершен"}
                  </span>
                </div>
              </div>

              <button
                onClick={handleCloseOverlay}
                className="p-1 rounded-lg hover:bg-white/5 text-zinc-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Sound Wave Animation Visualizer */}
            <div className="h-28 bg-zinc-950 border-b border-white/5 relative flex flex-col items-center justify-center">
              <canvas ref={canvasRef} width={450} height={100} className="w-full h-full opacity-80" />
              
              <div className="absolute bottom-2 text-[10px] font-mono text-zinc-500 uppercase tracking-widest">
                {callState === "dialing" ? "Гудки вызова..." : isSpeaking ? "ИИ Говорит..." : (isListening && !isMuted) ? "ИИ Слушает вас..." : "Пауза"}
              </div>
            </div>

            {/* Transcript Log */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-zinc-900/10">
              {messages.map((msg, idx) => {
                if (msg.sender === "system") {
                  return (
                    <div key={idx} className="flex justify-center">
                      <span className="px-3 py-1 bg-white/5 border border-white/5 text-[10px] font-mono text-zinc-400 rounded-full">
                        [{msg.time}] {msg.text}
                      </span>
                    </div>
                  );
                }

                const isBot = msg.sender === "bot";
                return (
                  <div key={idx} className={`flex ${isBot ? "justify-start" : "justify-end"} items-end gap-2`}>
                    {isBot && (
                      <div className="w-6 h-6 rounded-full bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-[10px] text-purple-400 font-bold shrink-0">
                        AI
                      </div>
                    )}
                    <div
                      className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm ${
                        isBot
                          ? "bg-zinc-900 text-white rounded-bl-none border border-white/5"
                          : "bg-purple-600 text-white rounded-br-none"
                      }`}
                    >
                      <p className="leading-relaxed">{msg.text}</p>
                      <span className="text-[9px] text-white/40 block text-right mt-1 font-mono">{msg.time}</span>
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Controls & Text Input Box */}
            <div className="p-4 border-t border-white/10 bg-zinc-900/30 space-y-3">
              {callState === "connected" && (
                <form onSubmit={handleFormSubmit} className="flex gap-2">
                  <input
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Напишите ответ или говорите в микрофон..."
                    className="flex-1 bg-black border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500 transition-colors"
                  />
                  <button
                    type="submit"
                    className="p-2 rounded-lg bg-white text-black hover:bg-zinc-200 transition-colors"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </form>
              )}

              {/* Action Buttons Panel */}
              <div className="flex items-center justify-center gap-6 pt-2">
                {callState === "connected" && (
                  <button
                    onClick={toggleMute}
                    className={`w-11 h-11 rounded-full border flex items-center justify-center transition-all ${
                      isMuted
                        ? "bg-red-500/20 border-red-500 text-red-400"
                        : "bg-white/5 border-white/10 text-zinc-400 hover:text-white"
                    }`}
                    title={isMuted ? "Включить микрофон" : "Выключить микрофон"}
                  >
                    {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                  </button>
                )}

                {callState === "dialing" || callState === "connected" ? (
                  <button
                    onClick={handleEndCall}
                    className="w-14 h-14 rounded-full bg-red-600 hover:bg-red-500 text-white flex items-center justify-center transition-all hover:scale-105 shadow-lg shadow-red-600/20 cursor-pointer"
                    title="Завершить вызов"
                  >
                    <PhoneOff className="w-6 h-6 fill-current" />
                  </button>
                ) : (
                  <button
                    onClick={handleStartCall}
                    className="w-14 h-14 rounded-full bg-emerald-600 hover:bg-emerald-500 text-white flex items-center justify-center transition-all hover:scale-105 shadow-lg shadow-emerald-600/20 cursor-pointer"
                    title="Начать звонок"
                  >
                    <Phone className="w-6 h-6 fill-current animate-pulse" />
                  </button>
                )}

                {callState === "connected" && (
                  <div className="w-11 h-11 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-zinc-400">
                    <Volume2 className="w-5 h-5 text-purple-400 animate-pulse" />
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
