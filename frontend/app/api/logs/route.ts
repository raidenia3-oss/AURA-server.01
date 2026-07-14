import { NextResponse } from "next/server";
import logger from "../../../lib/logger";

export const runtime = "nodejs";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const auth =
    request.headers.get("authorization") || url.searchParams.get("token");
  const expected = process.env.LOG_VIEW_TOKEN;

  if (expected && auth !== expected) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const limit = Number(url.searchParams.get("limit") || 100);
  logger.api("GET", "/api/logs", 0, 200);

  return NextResponse.json({ logs: logger.getLogs(limit) });
}
