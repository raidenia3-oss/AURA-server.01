import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useRef, useState } from "react";
import { getKnowledgeStats, ingestText } from "../services/api";

export default function KnowledgeBase() {
    const [text, setText] = useState("");
    const [status, setStatus] = useState<{
        stage: "idle" | "ingesting" | "done" | "error";
        message: string;
    }>({ stage: "idle", message: "" });
    const [count, setCount] = useState<number | null>(null);
    const [dragging, setDragging] = useState(false);
    const fileRef = useRef<HTMLInputElement>(null);

    const handleIngest = useCallback(async () => {
        const payload = text.trim();
        if (!payload) return;
        setStatus({ stage: "ingesting", message: "Indexando en la Base Vectorial... 🧠" });
        try {
            const result = await ingestText(payload, "ui-manual");
            if (result.status === "ok") {
                setStatus({
                    stage: "done",
                    message: `✅ ${result.chunks} fragmento(s) indexado(s) (${result.total_chars} caracteres)`,
                });
                setCount(result.total_in_db);
            } else {
                setStatus({ stage: "error", message: `❌ Error: ${result.status}` });
            }
        } catch (e: unknown) {
            setStatus({
                stage: "error",
                message: `❌ Error de conexión: ${e instanceof Error ? e.message : String(e)}`,
            });
        }
    }, [text]);

    const handleFile = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const content = await file.text();
        setText(content);
        setStatus({
            stage: "idle",
            message: `📄 Archivo cargado: ${file.name} (${content.length} chars)`,
        });
    }, []);

    const handleDrop = useCallback(async (e: React.DragEvent) => {
        e.preventDefault();
        setDragging(false);
        const file = e.dataTransfer.files?.[0];
        if (!file) return;
        const content = await file.text();
        setText(content);
        setStatus({
            stage: "idle",
            message: `📄 Archivo soltado: ${file.name} (${content.length} chars)`,
        });
    }, []);

    const fetchStats = useCallback(async () => {
        try {
            const data = await getKnowledgeStats();
            setCount(data.total_entries);
        } catch {
            setCount(null);
        }
    }, []);

    return (
        <div className="px-4 py-3 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-aura-green mb-1">
                🧠 Base de Conocimiento
            </h3>

            {/* Drop zone */}
            <div
                onDrop={handleDrop}
                onDragOver={(e) => {
                    e.preventDefault();
                    setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                className={`relative border-2 border-dashed rounded-lg p-3 text-center text-xs transition ${
                    dragging ? "border-aura-cyan bg-aura-cyan/10" : "border-white/10 bg-aura-bg"
                }`}
            >
                {dragging ? (
                    <span className="text-aura-cyan">📂 Suelta el archivo aquí</span>
                ) : (
                    <span className="text-aura-muted">
                        Arrastra un archivo .txt / .md o haz clic para buscar
                    </span>
                )}
                <input
                    ref={fileRef}
                    type="file"
                    accept=".txt,.md,.json,.yaml,.yml,.py,.js,.ts,.html,.css"
                    className="absolute inset-0 opacity-0 cursor-pointer"
                    onChange={handleFile}
                />
            </div>

            {/* Textarea */}
            <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="O pega texto directamente (docs, notas, config)..."
                rows={4}
                className="w-full bg-aura-bg border border-white/10 rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-aura-green/50 resize-none"
            />

            {/* Ingest button */}
            <button
                onClick={handleIngest}
                disabled={status.stage === "ingesting" || !text.trim()}
                className="w-full py-2 text-xs bg-aura-green/20 border border-aura-green/40 text-aura-green rounded-lg disabled:opacity-40 transition hover:bg-aura-green/30"
            >
                {status.stage === "ingesting" ? (
                    <span className="flex items-center justify-center gap-2">
                        <motion.span
                            animate={{ rotate: 360 }}
                            transition={{ repeat: Infinity, duration: 1 }}
                            className="inline-block"
                        >
                            🧠
                        </motion.span>
                        Indexando...
                    </span>
                ) : (
                    "🧠 Entrenar a AURA"
                )}
            </button>

            {/* Status animations */}
            <AnimatePresence>
                {status.stage === "done" && (
                    <motion.p
                        initial={{ opacity: 0, y: -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="text-xs text-aura-green"
                    >
                        {status.message}
                    </motion.p>
                )}
                {status.stage === "error" && (
                    <motion.p
                        initial={{ opacity: 0, y: -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="text-xs text-red-400"
                    >
                        {status.message}
                    </motion.p>
                )}
                {status.stage === "idle" && status.message && (
                    <p className="text-xs text-aura-muted">{status.message}</p>
                )}
            </AnimatePresence>

            {/* Stats */}
            <button
                onClick={fetchStats}
                className="w-full py-1.5 text-xs bg-aura-purple/20 border border-aura-purple/40 text-aura-purple rounded-lg hover:bg-aura-purple/30 transition"
            >
                {count !== null
                    ? `📊 ${count} fragmento(s) en la base vectorial`
                    : "📊 Ver estadísticas"}
            </button>
        </div>
    );
}
