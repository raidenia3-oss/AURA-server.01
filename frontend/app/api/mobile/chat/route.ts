// TODO: Cline will implement in Phase 58
// POST /api/mobile/chat
// Body: { ameId, message, imageUri? }
// Returns: { ameId, userMessage, ameResponse, timestamp }

import { NextResponse } from "next/server";

export async function POST(_request: Request) {
  return NextResponse.json(
    { error: "Not implemented yet" },
    { status: 501 },
  );
}
