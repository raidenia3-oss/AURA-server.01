import { NextRequest, NextResponse } from "next/server";
import { WebhookManager } from "../../../lib/webhook-manager";
import logger from "../../../lib/logger";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const action = url.searchParams.get("action");

  logger.api("GET", "/api/webhooks", 0, 200);

  if (action === "list") {
    return NextResponse.json({ webhooks: WebhookManager.getAll() });
  }

  return NextResponse.json({
    webhooks: WebhookManager.getAll(),
    documentation: {
      register: "POST /api/webhooks with { id, url, events }",
      unregister: "DELETE /api/webhooks?id=<id>",
      trigger: "POST /api/webhooks/trigger with { event, data }",
    },
  });
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    if (body.id && body.url && body.events) {
      const result = WebhookManager.register(body.id, body.url, body.events);
      logger.event("webhook registered", {
        id: body.id,
        url: body.url,
        events: body.events,
      });
      return NextResponse.json({ success: true, webhook: result });
    }

    if (body.event && body.data) {
      const results = await WebhookManager.trigger(body.event, body.data);
      logger.event("webhook triggered", { event: body.event });
      return NextResponse.json({ success: true, results });
    }

    logger.warn(
      "webhooks",
      "invalid payload",
      { id: body.id, event: body.event },
    );
    return NextResponse.json(
      { error: "Invalid payload. Expected { id, url, events } or { event, data }" },
      { status: 400 },
    );
  } catch (error) {
    logger.error("webhooks", "POST failed", error);
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const url = new URL(request.url);
    const id = url.searchParams.get("id");

    if (!id) {
      return NextResponse.json({ error: "Missing id parameter" }, { status: 400 });
    }

    const result = WebhookManager.unregister(id);
    return NextResponse.json({ success: true, result });
    } catch (error) {
      logger.error("webhooks", "DELETE failed", error);
      return NextResponse.json({ error: "Internal error" }, { status: 500 });
    }
  }
