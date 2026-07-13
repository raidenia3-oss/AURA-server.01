import { GoogleGenerativeAI } from "@google/generative-ai";
import { NextResponse, NextRequest } from "next/server";
import rateLimit from "../../../lib/rateLimit";
import { authenticate } from "../../../lib/authenticate";

const limiter = rateLimit(10, 60 * 1000); // 10 requests per minute

export async function POST(request: NextRequest) {
  const authResult = authenticate(request);
  if (authResult) {
    return authResult;
  }

  if (!limiter(request, NextResponse)) {
    return NextResponse.json({ error: "Too Many Requests" }, { status: 429 });
  }
  try {
    const { prompt } = await request.json();

    if (!process.env.GEMINI_API_KEY) {
      return NextResponse.json(
        { error: "GEMINI_API_KEY not configured" },
        { status: 500 },
      );
    }

    const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
    const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

    const result = await model.generateContent(prompt);
    const response = await result.response;
    const text = response.text();

    return NextResponse.json({ result: text });
  } catch (error) {
    console.error("Error in AME Core API:", error);
    return NextResponse.json(
      { error: "Failed to process request" },
      { status: 500 },
    );
  }
}
