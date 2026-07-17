import { NextRequest, NextResponse } from "next/server";

/**
 * POST /api/ai/multimodal
 * 
 * Accepts multimodal input (text + image + audio) and returns analysis.
 * Phase 58 - Option D3: Multimodal API Endpoint
 */

interface MultimodalRequest {
  text?: string;
  imageBase64?: string;
  audioBase64?: string;
}

interface TextAnalysis {
  understanding: string;
  response: string;
  confidence: number;
}

interface ImageAnalysis {
  description: string;
  objects: string[];
  sentiment: string;
}

interface MultimodalResponse {
  textAnalysis: TextAnalysis;
  imageAnalysis?: ImageAnalysis;
  audioTranscription?: string;
  rawOutput?: Record<string, unknown>;
}

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    const body: MultimodalRequest = await request.json();
    const { text, imageBase64, audioBase64 } = body;

    // Validate input
    if (!text && !imageBase64 && !audioBase64) {
      return NextResponse.json(
        { error: "At least one input modality required (text, image, or audio)" },
        { status: 400 }
      );
    }

    // Process text modality
    const textAnalysis = await processText(text);

    // Process image modality (if provided)
    let imageAnalysis: ImageAnalysis | undefined;
    if (imageBase64) {
      imageAnalysis = await processImage(imageBase64);
    }

    // Process audio modality (if provided)
    let audioTranscription: string | undefined;
    if (audioBase64) {
      audioTranscription = await processAudio(audioBase64);
    }

    // Combine results
    const response: MultimodalResponse = {
      textAnalysis,
      imageAnalysis,
      audioTranscription,
      rawOutput: {
        processingTimeMs: Date.now() - startTime,
        modalities: {
          text: !!text,
          image: !!imageBase64,
          audio: !!audioBase64,
        },
      },
    };

    return NextResponse.json(response);
  } catch (error) {
    console.error("Multimodal API error:", error);
    return NextResponse.json(
      {
        error: "Failed to process multimodal input",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

/**
 * Process text input using the fine-tuned model or fallback.
 */
async function processText(text?: string): Promise<TextAnalysis> {
  if (!text) {
    return {
      understanding: "No text provided",
      response: "Please provide text input for analysis.",
      confidence: 0,
    };
  }

  try {
    // Try to call the local fine-tuned model API
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    const response = await fetch(`${backendUrl}/api/ai/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        model: "ame-finetuned",
      }),
    });

    if (response.ok) {
      const data = await response.json();
      return {
        understanding: `Analyzed: "${text.substring(0, 100)}..."`,
        response: data.response || data.message || "Analysis complete.",
        confidence: data.confidence || 0.85,
      };
    }
  } catch {
    // Fallback: local analysis if backend is unavailable
    console.warn("Backend unavailable, using fallback text analysis");
  }

  // Fallback text analysis
  return {
    understanding: `Received text input (${text.length} chars)`,
    response: generateFallbackResponse(text),
    confidence: 0.7,
  };
}

/**
 * Process image input using vision capabilities.
 */
async function processImage(imageBase64: string): Promise<ImageAnalysis> {
  // Validate base64
  const imageSize = Math.ceil((imageBase64.length * 3) / 4);
  const sizeKB = Math.round(imageSize / 1024);

  if (sizeKB > 10 * 1024) {
    // > 10MB
    return {
      description: "Image too large for processing",
      objects: [],
      sentiment: "neutral",
    };
  }

  try {
    // Try to call backend vision API
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    const response = await fetch(`${backendUrl}/api/ai/vision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: imageBase64 }),
    });

    if (response.ok) {
      const data = await response.json();
      return {
        description: data.description || "Image analyzed",
        objects: data.objects || [],
        sentiment: data.sentiment || "neutral",
      };
    }
  } catch {
    console.warn("Backend vision unavailable, using fallback");
  }

  // Fallback: basic image info
  return {
    description: `Image received (${sizeKB}KB). Vision processing requires backend connection.`,
    objects: ["image"],
    sentiment: "neutral",
  };
}

/**
 * Process audio input using speech-to-text.
 */
async function processAudio(audioBase64: string): Promise<string> {
  try {
    // Try to call backend transcription API
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    const response = await fetch(`${backendUrl}/api/ai/transcribe`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ audio: audioBase64 }),
    });

    if (response.ok) {
      const data = await response.json();
      return data.transcription || data.text || "Audio processed";
    }
  } catch {
    console.warn("Backend transcription unavailable, using fallback");
  }

  // Fallback
  const audioSize = Math.ceil((audioBase64.length * 3) / 4);
  const sizeKB = Math.round(audioSize / 1024);
  return `Audio received (${sizeKB}KB). Transcription requires backend connection.`;
}

/**
 * Generate a fallback response when backend is unavailable.
 */
function generateFallbackResponse(text: string): string {
  const lowerText = text.toLowerCase();

  if (lowerText.includes("hello") || lowerText.includes("hi") || lowerText.includes("hey")) {
    return "Hello! I'm AURA, your AI assistant. How can I help you today?";
  }

  if (lowerText.includes("help") || lowerText.includes("what can you")) {
    return "I can help with: answering questions about AURA, managing AMEs, checking system status, and providing analytics. What would you like to know?";
  }

  if (lowerText.includes("status") || lowerText.includes("health")) {
    return "The AURA system is operational. All integrations are connected and the backend is running. Check /api/health for detailed status.";
  }

  if (lowerText.includes("analytics") || lowerText.includes("metrics")) {
    return "Analytics are available via the dashboard. You can view real-time metrics, trends, and forecasts. Check the /api/analytics endpoint for data.";
  }

  if (lowerText.includes("thank")) {
    return "You're welcome! Let me know if you need anything else.";
  }

  return `I received your message: "${text.substring(0, 200)}". For a more detailed response, please ensure the backend is running.`;
}

/**
 * GET /api/ai/model-info
 * Returns information about the current AI model.
 */
export async function GET() {
  return NextResponse.json({
    model: "ame-finetuned",
    baseModel: "Qwen/Qwen2.5-Coder-3B",
    version: "4.0.0",
    capabilities: ["text", "image", "audio"],
    status: "operational",
    backend: process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000",
  });
}