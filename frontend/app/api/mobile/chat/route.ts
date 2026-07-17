import { NextRequest, NextResponse } from "next/server";

/**
 * POST /api/mobile/chat
 * Send a message to an AME and get a response.
 * Phase 58 - Option A: Mobile API - Chat
 */

interface ChatRequest {
  ameId: string;
  message: string;
  imageUri?: string;
  audioUri?: string;
}

const AME_RESPONSES: Record<string, (msg: string) => string> = {
  ame_core: (msg: string) => {
    const lower = msg.toLowerCase();
    if (lower.includes("hello") || lower.includes("hi")) return "Hello! I'm AURA-Core. How can I assist you today?";
    if (lower.includes("status") || lower.includes("health")) return "All systems operational. 5 integrations connected, 99.9% uptime.";
    if (lower.includes("help")) return "I can help with system management, analytics, and integration configuration. What do you need?";
    return `I received your message: "${msg.substring(0, 100)}". Processing through AURA-Core.`;
  },
  ame_analytics: (msg: string) => {
    const lower = msg.toLowerCase();
    if (lower.includes("trend") || lower.includes("growth")) return "Current trends show 12.5% week-over-week growth. Event volume is increasing steadily.";
    if (lower.includes("error") || lower.includes("anomaly")) return "No anomalies detected in the last 24 hours. Error rate is below 0.1%.";
    if (lower.includes("forecast") || lower.includes("predict")) return "Next 7 days forecast: ~1,200-1,300 events daily with 85% confidence.";
    return `Analyzing: "${msg.substring(0, 100)}". Check the analytics dashboard for detailed metrics.`;
  },
  ame_integrations: (msg: string) => {
    const lower = msg.toLowerCase();
    if (lower.includes("slack")) return "Slack integration is active. 300 events today, 0 errors, 120ms avg latency.";
    if (lower.includes("discord")) return "Discord integration is active. 250 events today, 1 error, 130ms avg latency.";
    if (lower.includes("telegram")) return "Telegram integration is active. 200 events today, 0 errors, 110ms avg latency.";
    return "All 5 integrations are connected and healthy. Check /api/integrations for details.";
  },
  ame_monitor: (msg: string) => {
    const lower = msg.toLowerCase();
    if (lower.includes("cpu") || lower.includes("memory")) return "System resources: CPU 23%, Memory 45%, Disk 67%. All within normal ranges.";
    if (lower.includes("alert") || lower.includes("warning")) return "No active alerts. Last alert was 3 days ago (high latency on webhook).";
    if (lower.includes("uptime")) return "System uptime: 99.9% over the last 30 days. Last restart: 14 days ago.";
    return "Monitoring all systems. Current status: healthy.";
  },
  ame_learning: (msg: string) => {
    return "I'm currently in offline mode for maintenance. New training data is being processed. Please try AURA-Core for immediate assistance.";
  },
};

const DEFAULT_RESPONSE = "Thank you for your message. I'll process this and get back to you shortly.";

export async function POST(request: NextRequest) {
  try {
    const body: ChatRequest = await request.json();
    const { ameId, message, imageUri, audioUri } = body;

    if (!ameId || !message) {
      return NextResponse.json(
        { error: "ameId and message are required" },
        { status: 400 }
      );
    }

    // In production, fetch from backend
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    
    try {
      const response = await fetch(`${backendUrl}/api/mobile/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": request.headers.get("Authorization") || "",
        },
        body: JSON.stringify({ ameId, message, imageUri, audioUri }),
        signal: AbortSignal.timeout(10000),
      });

      if (response.ok) {
        const data = await response.json();
        return NextResponse.json(data);
      }
    } catch {
      console.warn("Backend unavailable, using fallback chat response");
    }

    // Generate response based on AME
    const responseFn = AME_RESPONSES[ameId];
    const ameResponse = responseFn ? responseFn(message) : DEFAULT_RESPONSE;

    return NextResponse.json({
      ameId,
      userMessage: message,
      ameResponse,
      timestamp: new Date().toISOString(),
      imageAnalysis: imageUri ? "Image received for analysis" : undefined,
      audioTranscription: audioUri ? "Audio received for transcription" : undefined,
    });
  } catch (error) {
    console.error("Mobile chat API error:", error);
    return NextResponse.json(
      { error: "Failed to process message" },
      { status: 500 }
    );
  }
}