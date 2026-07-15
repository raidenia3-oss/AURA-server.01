// TODO: Cline will implement in Phase 58
// PUT /api/mobile/sync
// Body: { lastSync }
// Returns: { changes, newLastSync }

import { NextResponse } from "next/server";

export async function PUT(_request: Request) {
  return NextResponse.json(
    { error: "Not implemented yet" },
    { status: 501 },
  );
}
