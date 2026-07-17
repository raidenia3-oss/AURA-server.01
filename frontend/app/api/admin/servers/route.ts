import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

// Proxies multi-server admin operations to the AME backend.
// GET  -> list servers
// POST -> { action: 'register'|'switch'|'deploy', server_type, credentials?, code_path? }
// PUT  -> { db_url } (sync DATABASE_URL to all registered targets)

function backendBase(): string | null {
  return process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || null;
}

export async function GET() {
  const backend = backendBase();
  if (!backend) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_URL no configurado" },
      { status: 501 },
    );
  }
  try {
    const res = await fetch(`${backend}/api/admin/servers`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ ok: false, error: "Backend AME no alcanzable" }, { status: 502 });
  }
}

export async function POST(req: NextRequest) {
  const backend = backendBase();
  if (!backend) {
    return NextResponse.json({ ok: false, error: "BACKEND_URL no configurado" }, { status: 501 });
  }
  try {
    const body = await req.json();
    const res = await fetch(`${backend}/api/admin/servers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ ok: false, error: "Backend AME no alcanzable" }, { status: 502 });
  }
}

export async function PUT(req: NextRequest) {
  const backend = backendBase();
  if (!backend) {
    return NextResponse.json({ ok: false, error: "BACKEND_URL no configurado" }, { status: 501 });
  }
  try {
    const body = await req.json();
    const res = await fetch(`${backend}/api/admin/servers`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ ok: false, error: "Backend AME no alcanzable" }, { status: 502 });
  }
}
