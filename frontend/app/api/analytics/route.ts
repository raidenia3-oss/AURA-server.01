import { NextRequest, NextResponse } from "next/server";
import { generateFallbackAnalytics, type AnalyticsResponse } from "@/lib/analyticsFallback";

/**
 * GET /api/analytics
 * 
 * Returns aggregated analytics data including summary, per-integration metrics,
 * trends, anomalies, and forecasts.
 * Phase 58 - Option F3: Analytics Endpoints
 */

interface AnalyticsSummary {
  total_events_today: number;
  total_errors: number;
  avg_latency_ms: number;
  integrations_connected: number;
  uptime_percent: number;
}

interface IntegrationMetrics {
  events: number;
  errors: number;
  latency: number;
  uptime: number;
}

interface TrendData {
  week_over_week: number;
  month_over_month: number;
  anomalies: Array<{
    date: string;
    type: string;
    severity: string;
    value: number;
    threshold: number;
  }>;
  trend: string;
  total_events_7d: number;
  total_events_30d: number;
}

interface ForecastData {
  next_7_days: number[];
  confidence: number;
  method: string;
  historical_avg: number;
  historical_trend: number;
  generated_at: string;
}

export async function GET(request: NextRequest) {
  try {
    // Try to get data from the analytics engine output
    const analyticsData = await fetchAnalyticsData();
    
    return NextResponse.json(analyticsData);
  } catch (error) {
    console.error("Analytics API error:", error);
    
    // Return fallback data if analytics engine is unavailable
    return NextResponse.json(generateFallbackAnalytics());
  }
}

/**
 * Fetch analytics data from the analytics engine output files.
 */
async function fetchAnalyticsData(): Promise<AnalyticsResponse> {
  try {
    // Try to read from the analytics engine output
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    const response = await fetch(`${backendUrl}/api/analytics`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(5000),
    });

    if (response.ok) {
      return await response.json();
    }
  } catch {
    console.warn("Backend analytics unavailable, using fallback data");
  }

  return generateFallbackAnalytics();
}

