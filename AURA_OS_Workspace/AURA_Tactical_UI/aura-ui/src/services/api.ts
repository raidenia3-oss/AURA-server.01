const BASE = "http://localhost:8000";

export interface HealthStatus {
    status: string;
    providers: Record<string, { status: string; latency_s: number | null }>;
}

export interface ChatResult {
    session_id: number;
    response: string;
    provider_used: string;
    intention: string;
    tool_used: string | null;
    tool_output: Record<string, unknown> | null;
    tool_pending: { tool: string; args: Record<string, unknown> } | null;
    tool_risky: boolean | null;
    rag_used: boolean;
}

export interface SessionInfo {
    session_id: number;
    messages_count: number;
    last_role: string;
    last_ts: string;
}

export interface IngestResult {
    status: string;
    doc_id: string;
    chunks: number;
    total_chars: number;
    total_in_db: number;
}

export async function getHealth(): Promise<HealthStatus> {
    const res = await fetch(`${BASE}/health`);
    return res.json();
}

export async function listSessions(limit = 50): Promise<SessionInfo[]> {
    const res = await fetch(`${BASE}/sessions?limit=${limit}`);
    const data = await res.json();
    return data.sessions ?? [];
}

export async function sendChat(
    message: string,
    sessionId?: number,
    persona?: string,
    provider?: string,
    toolAuthorized?: Record<string, unknown>,
): Promise<ChatResult> {
    const res = await fetch(`${BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            message,
            session_id: sessionId ?? null,
            persona: persona ?? null,
            provider: provider ?? null,
            tool_authorized: toolAuthorized ?? null,
        }),
    });
    return res.json();
}

export async function ingestText(text: string, source = "ui-manual"): Promise<IngestResult> {
    const res = await fetch(`${BASE}/ingest-text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, source }),
    });
    return res.json();
}

export async function getKnowledgeStats(): Promise<{ total_entries: number }> {
    const res = await fetch(`${BASE}/knowledge/stats`);
    return res.json();
}

export async function analyzeImage(
    imageBase64: string,
    prompt: string,
    sessionId?: number,
): Promise<{
    session_id: number;
    response: string;
    provider_used: string;
}> {
    const res = await fetch(`${BASE}/analyze-image`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_base64: imageBase64, prompt, session_id: sessionId }),
    });
    return res.json();
}

export async function transcribeAudio(
    file: File,
    prompt?: string,
): Promise<{
    session_id: number;
    transcription: string;
    provider: string;
}> {
    const form = new FormData();
    form.append("file", file);
    if (prompt) form.append("prompt", prompt);

    const res = await fetch(`${BASE}/transcribe`, {
        method: "POST",
        body: form,
    });
    return res.json();
}
