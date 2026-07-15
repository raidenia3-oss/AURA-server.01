// TODO: Cline will implement in Phase 58
// GET /api/mobile/ames
// Returns: { ames: [{id, name, status, lastActivity, unreadCount}] }

import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json(
    { error: "Not implemented yet" },
    { status: 501 },
  );
}
