import { motion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { analyzeImage, sendChat, transcribeAudio } from "../services/api";
import MessageItem, { MessageData } from "./MessageItem";

export default function ChatPanel({ persona, provider }: { persona: string; provider: string }) {
    const [messages, setMessages] = useState<MessageData[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [sessionId, setSessionId] = useState<number | undefined>(undefined);
    const [pendingImage, setPendingImage] = useState<string | null>(null);
    const bottomRef = useRef<HTMLDivElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const send = useCallback(async () => {
        const text = input.trim();
        if (!text && !pendingImage) return;
        if (loading) return;

        const userMsg: MessageData = {
            id: `user-${Date.now()}`,
            role: "user",
            content: pendingImage ? text || "(Imagen adjunta)" : text,
            image: pendingImage || undefined,
        };
        setMessages((m) => [...m, userMsg]);
        setInput("");
        setLoading(true);
        setPendingImage(null);

        const streamId = `stream-${Date.now()}`;
        setMessages((m) => [
            ...m,
            { id: streamId, role: "assistant", content: "", isStreaming: true },
        ]);

        try {
            let result: {
                session_id: number;
                response?: string;
                provider_used?: string;
                tool_used?: string | null;
                tool_output?: Record<string, unknown> | null;
            };

            if (pendingImage) {
                const prompt =
                    text ||
                    "Describe esta imagen con el mayor detalle posible. Si hay texto, transcribelo. Si hay elementos visuales relevantes, identificalos.";
                const imgResult = (await analyzeImage(
                    pendingImage,
                    prompt,
                    sessionId,
                )) as unknown as {
                    session_id: number;
                    response: string;
                    provider_used: string;
                };
                setSessionId(imgResult.session_id);
                result = {
                    session_id: imgResult.session_id,
                    response: imgResult.response,
                    provider_used: imgResult.provider_used,
                    tool_used: null,
                    tool_output: null,
                };
            } else {
                const chatResult = await sendChat(
                    text,
                    sessionId,
                    persona,
                    provider !== "Automático" ? provider : undefined,
                );
                setSessionId(chatResult.session_id);
                result = {
                    session_id: chatResult.session_id,
                    response: chatResult.response,
                    provider_used: chatResult.provider_used,
                    tool_used: chatResult.tool_used,
                    tool_output: chatResult.tool_output ?? undefined,
                };
            }

            setMessages((m) =>
                m.map((msg) =>
                    msg.id === streamId
                        ? {
                              id: `assistant-${Date.now()}`,
                              role: "assistant",
                              content: result?.response || "Sin respuesta",
                              provider: result?.provider_used,
                              tool: result?.tool_used,
                              toolOutput: result?.tool_output ?? undefined,
                          }
                        : msg,
                ),
            );
        } catch (e) {
            setMessages((m) =>
                m.map((msg) =>
                    msg.id === streamId
                        ? { id: `err-${Date.now()}`, role: "assistant", content: `Error: ${e}` }
                        : msg,
                ),
            );
        } finally {
            setLoading(false);
        }
    }, [input, loading, sessionId, persona, provider, pendingImage]);

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="px-6 py-4 border-b border-white/5 flex items-center gap-3">
                <motion.div
                    animate={{ opacity: [0.6, 1, 0.6] }}
                    transition={{ repeat: Infinity, duration: 2 }}
                    className="w-2 h-2 rounded-full bg-aura-green"
                />
                <h1 className="text-lg font-semibold tracking-wide text-aura-cyan">AURA</h1>
                <span className="text-xs text-aura-muted">
                    {persona} · {provider}
                </span>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
                {messages.length === 0 && (
                    <div className="flex items-center justify-center h-full text-aura-muted text-sm">
                        Envía un mensaje para empezar a conversar con AURA...
                    </div>
                )}
                {messages.map((msg) => (
                    <MessageItem key={msg.id} msg={msg} />
                ))}
                <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="p-4 border-t border-white/5 space-y-2">
                {pendingImage && (
                    <div className="flex items-center gap-2">
                        <img
                            src={pendingImage}
                            alt="Vista previa"
                            className="h-12 w-auto rounded border border-white/10"
                        />
                        <button
                            onClick={() => setPendingImage(null)}
                            className="text-xs text-red-400 hover:text-red-300"
                        >
                            ✕
                        </button>
                    </div>
                )}
                <div className="flex gap-2">
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*,audio/*"
                        className="hidden"
                        onChange={async (e) => {
                            const file = e.target.files?.[0];
                            if (!file) return;
                            if (file.type.startsWith("audio/")) {
                                await transcribeAudio(file);
                                return;
                            }
                            const reader = new FileReader();
                            reader.onload = () => {
                                const b64 = (reader.result as string).split(",")[1];
                                setPendingImage(b64);
                            };
                            reader.readAsDataURL(file);
                        }}
                    />
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        className="px-3 py-2 bg-aura-bg border border-white/10 rounded-xl text-sm hover:border-aura-cyan/50 transition"
                        title="Adjuntar imagen o audio"
                    >
                        📎
                    </button>
                    <input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && send()}
                        placeholder="Escribe un mensaje a AURA..."
                        disabled={loading}
                        className="flex-1 bg-aura-panel border border-white/10 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-aura-cyan/50 disabled:opacity-40"
                    />
                    <button
                        onClick={send}
                        disabled={loading || (!input.trim() && !pendingImage)}
                        className="px-5 py-2.5 bg-aura-cyan/20 border border-aura-cyan/40 text-aura-cyan rounded-xl text-sm hover:bg-aura-cyan/30 transition disabled:opacity-40"
                    >
                        {loading ? "..." : "Enviar"}
                    </button>
                </div>
            </div>
        </div>
    );
}
