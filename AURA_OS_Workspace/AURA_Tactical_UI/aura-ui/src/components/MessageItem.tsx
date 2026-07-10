import { motion } from "framer-motion";

export interface MessageData {
    id: string;
    role: "user" | "assistant";
    content: string;
    provider?: string;
    tool?: string | null;
    toolOutput?: Record<string, unknown> | null;
    isStreaming?: boolean;
    image?: string | null;
}

export default function MessageItem({
    msg,
    onApproveShell,
    onRejectShell,
}: {
    msg: MessageData;
    onApproveShell?: () => void;
    onRejectShell?: () => void;
}) {
    const isUser = msg.role === "user";
    const isPendingShell = msg.role === "assistant" && msg.content.includes("⚠️");

    const providerBadge = (p: string) => {
        const map: Record<string, string> = {
            ollama: "🟢 Local",
            openrouter: "🔵 OpenRouter",
            groq: "🟣 Groq",
            gemini: "🟠 Gemini",
        };
        return map[p] || `🔹 ${p}`;
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}
        >
            {/* Avatar */}
            <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                    isUser
                        ? "bg-aura-blue/30 text-aura-blue border border-aura-blue/40"
                        : "bg-aura-cyan/20 text-aura-cyan border border-aura-cyan/40"
                }`}
            >
                {isUser ? "U" : "A"}
            </div>

            {/* Bubble */}
            <div className={`max-w-[75%] space-y-1 ${isUser ? "items-end" : "items-start"}`}>
                <div
                    className={`px-4 py-2 rounded-2xl text-sm leading-relaxed ${
                        isUser
                            ? "bg-aura-blue/20 text-white rounded-tr-sm"
                            : "bg-aura-panel border border-white/5 text-gray-100 rounded-tl-sm"
                    }`}
                >
                    {msg.image && (
                        <img
                            src={msg.image}
                            alt="Adjunto"
                            className="mb-2 rounded border border-white/10 max-w-[240px]"
                        />
                    )}
                    {msg.content}
                    {msg.isStreaming && <span className="inline-block ml-1 animate-pulse">▊</span>}
                </div>

                {/* Provider badge */}
                {!isUser && msg.provider && (
                    <span className="text-[10px] text-aura-muted px-1">
                        {providerBadge(msg.provider)}
                    </span>
                )}

                {/* Tool usage */}
                {!isUser && msg.tool && (
                    <details className="text-xs text-aura-muted bg-aura-bg rounded-lg px-2 py-1 border border-white/5">
                        <summary className="cursor-pointer text-aura-cyan">🛠️ {msg.tool}</summary>
                        {msg.toolOutput && (
                            <pre className="mt-1 overflow-x-auto text-[10px] text-gray-400">
                                {JSON.stringify(msg.toolOutput, null, 2)}
                            </pre>
                        )}
                    </details>
                )}

                {/* Shell auth */}
                {isPendingShell && (
                    <div className="flex gap-2 mt-1">
                        <button
                            onClick={onApproveShell}
                            className="px-3 py-1 text-xs bg-green-600/20 text-green-400 border border-green-600/40 rounded-lg"
                        >
                            ✅ Aprobar
                        </button>
                        <button
                            onClick={onRejectShell}
                            className="px-3 py-1 text-xs bg-red-600/20 text-red-400 border border-red-600/40 rounded-lg"
                        >
                            ❌ Rechazar
                        </button>
                    </div>
                )}
            </div>
        </motion.div>
    );
}
