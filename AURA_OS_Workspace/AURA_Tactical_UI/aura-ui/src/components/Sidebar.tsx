import { useEffect, useState } from "react";
import { getHealth, listSessions, type HealthStatus, type SessionInfo } from "../services/api";
import KnowledgeBase from "./KnowledgeBase";

export default function Sidebar({
    persona,
    onPersonaChange,
    provider,
    onProviderChange,
}: {
    persona: string;
    onPersonaChange: (v: string) => void;
    provider: string;
    onProviderChange: (v: string) => void;
}) {
    const [sessions, setSessions] = useState<SessionInfo[]>([]);
    const [health, setHealth] = useState<HealthStatus | null>(null);
    const [showKb, setShowKb] = useState(false);

    useEffect(() => {
        getHealth()
            .then(setHealth)
            .catch(() => setHealth(null));
        listSessions()
            .then(setSessions)
            .catch(() => setSessions([]));
    }, []);

    const availableProviders = health
        ? Object.entries(health.providers).filter(([, v]) => v.status === "ok").length
        : 0;
    const totalProviders = health ? Object.keys(health.providers).length : 0;

    return (
        <aside className="bg-aura-panel border-r border-white/5 flex flex-col h-full overflow-y-auto">
            <div className="p-4 border-b border-white/5">
                <h2 className="text-sm font-semibold uppercase tracking-widest text-aura-muted">
                    AURA Control
                </h2>
            </div>

            <div className="p-4 space-y-6">
                {/* Persona */}
                <div>
                    <label className="block text-xs text-aura-muted mb-1">Persona / Agente</label>
                    <select
                        value={persona}
                        onChange={(e) => onPersonaChange(e.target.value)}
                        className="w-full bg-aura-bg border border-white/10 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-aura-cyan/50"
                    >
                        <option>AURA Standard</option>
                        <option>Senior Architect</option>
                        <option>Creative</option>
                    </select>
                </div>

                {/* Provider mode */}
                <div>
                    <label className="block text-xs text-aura-muted mb-1">Modo</label>
                    <div className="flex gap-1">
                        {["Automático", "Solo Local", "Solo Nube"].map((opt) => (
                            <button
                                key={opt}
                                onClick={() => onProviderChange(opt)}
                                className={`flex-1 text-xs py-1.5 rounded ${
                                    provider === opt
                                        ? "bg-aura-cyan/20 text-aura-cyan border border-aura-cyan/40"
                                        : "bg-aura-bg text-aura-muted border border-white/5"
                                }`}
                            >
                                {opt === "Automático"
                                    ? "Auto"
                                    : opt === "Solo Local"
                                      ? "Local"
                                      : "Nube"}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Server status */}
                <div className="border-t border-white/5 pt-4">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-aura-muted mb-2">
                        🌐 Estado del Servidor
                    </h3>
                    <div className="space-y-1 text-xs">
                        <p className="flex justify-between">
                            <span className="text-aura-muted">API</span>
                            <span
                                className={
                                    health?.status === "ok" ? "text-aura-green" : "text-red-400"
                                }
                            >
                                {health?.status === "ok" ? "🟢 Online" : "🔴 Offline"}
                            </span>
                        </p>
                        <p className="flex justify-between">
                            <span className="text-aura-muted">IA disponibles</span>
                            <span className="text-white">
                                {availableProviders}/{totalProviders}
                            </span>
                        </p>
                        {health?.providers?.ollama && (
                            <p className="flex justify-between">
                                <span className="text-aura-muted">Ollama</span>
                                <span
                                    className={
                                        health.providers.ollama.status === "ok"
                                            ? "text-aura-green"
                                            : "text-red-400"
                                    }
                                >
                                    {health.providers.ollama.status === "ok" ? "✅" : "❌"}
                                </span>
                            </p>
                        )}
                    </div>
                </div>

                {/* Sessions */}
                <div className="border-t border-white/5 pt-4">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-aura-muted mb-2">
                        💬 Sesiones
                    </h3>
                    <div className="space-y-1 max-h-32 overflow-y-auto">
                        {sessions.length === 0 && (
                            <p className="text-xs text-aura-muted">Sin sesiones aún</p>
                        )}
                        {sessions.map((s) => (
                            <div
                                key={s.session_id}
                                className="text-xs text-aura-muted bg-aura-bg rounded px-2 py-1 truncate"
                            >
                                #{s.session_id} · {s.messages_count} msgs · {s.last_role}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Knowledge Base toggle */}
                <div className="border-t border-white/5 pt-4">
                    <button
                        onClick={() => setShowKb(!showKb)}
                        className="w-full py-2 text-xs bg-aura-green/15 border border-aura-green/30 text-aura-green rounded-lg"
                    >
                        {showKb ? "▾ Ocultar KB" : "▸ Base de Conocimiento"}
                    </button>
                    {showKb && <KnowledgeBase />}
                </div>

                {/* Nueva Sesión */}
                <div>
                    <button
                        onClick={() => window.location.reload()}
                        className="w-full py-2 text-sm bg-aura-purple/20 border border-aura-purple/40 text-aura-purple rounded-lg hover:bg-aura-purple/30 transition"
                    >
                        + Nueva Sesión
                    </button>
                </div>
            </div>
        </aside>
    );
}
