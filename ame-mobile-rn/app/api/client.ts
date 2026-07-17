import { getAuthToken } from "../../lib/firebase";
import AsyncStorage from "@react-native-async-storage/async-storage";

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000";
const OFFLINE_QUEUE_KEY = "offline-queue";

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  requiresAuth?: boolean;
}

interface OfflineQueueItem {
  endpoint: string;
  options: RequestOptions;
  timestamp: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async getHeaders(
    requiresAuth: boolean = false
  ): Promise<Record<string, string>> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (requiresAuth) {
      const token = await getAuthToken();
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
    }

    return headers;
  }

  async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { method = "GET", body, requiresAuth = false } = options;

    try {
      const headers = await this.getHeaders(requiresAuth);
      const config: RequestInit = {
        method,
        headers: { ...headers, ...options.headers },
      };

      if (body && method !== "GET") {
        config.body = JSON.stringify(body);
      }

      const response = await fetch(`${this.baseUrl}${endpoint}`, config);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `API Error ${response.status}: ${errorText || response.statusText}`
        );
      }

      return (await response.json()) as T;
    } catch (error) {
      // If offline, queue the request
      if (
        error instanceof TypeError &&
        error.message === "Network request failed"
      ) {
        await this.queueOfflineRequest(endpoint, options);
        throw new Error("Offline: request queued for sync");
      }
      throw error;
    }
  }

  private async queueOfflineRequest(
    endpoint: string,
    options: RequestOptions
  ): Promise<void> {
    try {
      const queueStr = await AsyncStorage.getItem(OFFLINE_QUEUE_KEY);
      const queue: OfflineQueueItem[] = queueStr ? JSON.parse(queueStr) : [];

      queue.push({
        endpoint,
        options,
        timestamp: new Date().toISOString(),
      });

      await AsyncStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(queue));
    } catch (error) {
      console.error("Failed to queue offline request:", error);
    }
  }

  async processOfflineQueue(): Promise<number> {
    try {
      const queueStr = await AsyncStorage.getItem(OFFLINE_QUEUE_KEY);
      if (!queueStr) return 0;

      const queue: OfflineQueueItem[] = JSON.parse(queueStr);
      let processed = 0;

      for (const item of queue) {
        try {
          await this.request(item.endpoint, item.options);
          processed++;
        } catch (error) {
          console.error("Failed to process queued request:", error);
          break; // Stop processing if still offline
        }
      }

      // Remove processed items
      const remaining = queue.slice(processed);
      await AsyncStorage.setItem(
        OFFLINE_QUEUE_KEY,
        JSON.stringify(remaining)
      );

      return processed;
    } catch (error) {
      console.error("Failed to process offline queue:", error);
      return 0;
    }
  }

  // API Methods

  async getAmes(): Promise<{ ames: Array<{ id: string; name: string; status: string; lastActivity: string; unreadCount: number }> }> {
    return this.request("/api/mobile/ames", { requiresAuth: true });
  }

  async sendMessage(
    ameId: string,
    message: string,
    imageUri?: string,
    audioUri?: string
  ): Promise<{
    ameId: string;
    userMessage: string;
    ameResponse: string;
    timestamp: string;
  }> {
    return this.request(
      "/api/mobile/chat",
      {
        method: "POST",
        body: { ameId, message, imageUri, audioUri },
        requiresAuth: true,
      }
    );
  }

  async sync(lastSync: string): Promise<{
    changes: Array<{ type: string; data: unknown }>;
    newLastSync: string;
  }> {
    return this.request("/api/mobile/sync", {
      method: "PUT",
      body: { lastSync },
      requiresAuth: true,
    });
  }

  async getAnalytics(): Promise<{
    summary: {
      total_events_today: number;
      total_errors: number;
      avg_latency_ms: number;
      integrations_connected: number;
      uptime_percent: number;
    };
    by_integration: Record<string, { events: number; errors: number; latency: number }>;
    trends: { week_over_week: number; anomalies: string[] };
    forecast: { next_7_days: number[]; confidence: number };
  }> {
    return this.request("/api/analytics", { requiresAuth: true });
  }

  async sendMultimodal(
    text?: string,
    imageBase64?: string,
    audioBase64?: string
  ): Promise<{
    textAnalysis: {
      understanding: string;
      response: string;
      confidence: number;
    };
    imageAnalysis?: {
      description: string;
      objects: string[];
      sentiment: string;
    };
    audioTranscription?: string;
  }> {
    return this.request("/api/ai/multimodal", {
      method: "POST",
      body: { text, imageBase64, audioBase64 },
      requiresAuth: true,
    });
  }
}

export const apiClient = new ApiClient();
export default ApiClient;