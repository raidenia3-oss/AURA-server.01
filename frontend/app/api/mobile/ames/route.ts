import { NextRequest, NextResponse } from "next/server";

/**
 * GET /api/mobile/ames
 * Returns list of AMEs for the authenticated user.
 * Phase 58 - Option A: Mobile API
 */

export async function GET(request: NextRequest) {
  try {
    // In production, fetch from backend
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    
    try {
      const response = await fetch(`${backendUrl}/api/mobile/ames`, {
        headers: {
          "Content-Type": "application/json",
          "Authorization": request.headers.get("Authorization") || "",
        },
        signal: AbortSignal.timeout(5000),
      });

      if (response.ok) {
        const data = await response.json();
        return NextResponse.json(data);
      }
    } catch {
      console.warn("Backend unavailable, using fallback AMEs data");
    }

    // Fallback data
    return NextResponse.json({
      ames: [
        {
          id: "ame_core",
          name: "AURA-Core",
          status: "online",
          lastActivity: new Date().toISOString(),
          unreadCount: 0,
        },
        {
          id: "ame_analytics",
          name: "Analytics-AME",
          status: "online",
          lastActivity: new Date(Date.now() - 3600000).toISOString(),
          unreadCount: 2,
        },
        {
          id: "ame_integrations",
          name: "Integrations-AME",
          status: "busy",
          lastActivity: new Date(Date.now() - 7200000).toISOString(),
          unreadCount: 0,
        },
        {
          id: "ame_monitor",
          name: "Monitor-AME",
          status: "online",
          lastActivity: new Date(Date.now() - 1800000).toISOString(),
          unreadCount: 5,
        },
        {
          id: "ame_learning",
          name: "Learning-AME",
          status: "offline",
          lastActivity: new Date(Date.now() - 86400000).toISOString(),
          unreadCount: 0,
        },
      ],
    });
  } catch (error) {
    console.error("Mobile AMEs API error:", error);
    return NextResponse.json(
      { error: "Failed to fetch AMEs" },
      { status: 500 }
    );
  }
}