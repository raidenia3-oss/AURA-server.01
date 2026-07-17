import { useState, useEffect, useCallback, useRef } from "react";
import { useAppStore, AME, Message } from "./store";
import { apiClient } from "../app/api/client";
import { onAuthChange, logout as firebaseLogout } from "./firebase";
import { Alert, AppState, AppStateStatus } from "react-native";

// Hook: Authentication
export function useAuth() {
  const { isAuthenticated, userEmail, setAuth, clearAuth } = useAppStore();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthChange((user) => {
      if (user) {
        user.getIdToken().then((token) => {
          setAuth(user.email || "", token);
          setIsLoading(false);
        });
      } else {
        clearAuth();
        setIsLoading(false);
      }
    });

    return unsubscribe;
  }, [setAuth, clearAuth]);

  const logout = useCallback(async () => {
    try {
      await firebaseLogout();
      clearAuth();
    } catch (error) {
      console.error("Logout failed:", error);
      Alert.alert("Error", "Failed to logout. Please try again.");
    }
  }, [clearAuth]);

  return { isAuthenticated, userEmail, isLoading, logout };
}

// Hook: AMEs list
export function useAmes() {
  const { ames, setAmes, isOfflineMode } = useAppStore();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAmes = useCallback(async () => {
    if (isOfflineMode) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.getAmes();
      setAmes(response.ames as AME[]);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch AMEs";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [setAmes, isOfflineMode]);

  useEffect(() => {
    fetchAmes();
  }, [fetchAmes]);

  return { ames, isLoading, error, refresh: fetchAmes };
}

// Hook: Chat messages
export function useChat(ameId: string | null) {
  const { messages, addMessage, setMessages, selectedAmeId } = useAppStore();
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentMessages = ameId ? messages[ameId] || [] : [];

  const sendMessage = useCallback(
    async (text: string, imageUri?: string, audioUri?: string) => {
      if (!ameId) return;
      setIsSending(true);
      setError(null);

      // Optimistic update
      const tempMessage: Message = {
        id: `temp-${Date.now()}`,
        ameId,
        role: "user",
        content: text,
        timestamp: new Date().toISOString(),
        imageUri,
        audioUri,
      };
      addMessage(ameId, tempMessage);

      try {
        const response = await apiClient.sendMessage(
          ameId,
          text,
          imageUri,
          audioUri
        );

        // Replace temp message with server response
        const serverMessage: Message = {
          id: `msg-${Date.now()}`,
          ameId,
          role: "ame",
          content: response.ameResponse,
          timestamp: response.timestamp,
        };
        addMessage(ameId, serverMessage);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to send message";
        setError(message);
        // Keep the optimistic message even on error (will sync later)
      } finally {
        setIsSending(false);
      }
    },
    [ameId, addMessage]
  );

  return {
    messages: currentMessages,
    isLoading,
    isSending,
    error,
    sendMessage,
  };
}

// Hook: Sync mechanism
export function useSync() {
  const { sync, setSyncState, isOfflineMode } = useAppStore();
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const performSync = useCallback(async () => {
    if (isOfflineMode) return;
    setSyncState({ isSyncing: true });

    try {
      // Process offline queue first
      const processed = await apiClient.processOfflineQueue();

      // Then sync with server
      const lastSync = sync.lastSync || new Date(0).toISOString();
      const result = await apiClient.sync(lastSync);

      setSyncState({
        lastSync: result.newLastSync,
        isSyncing: false,
        pendingChanges: result.changes.length,
      });

      // Process changes
      for (const change of result.changes) {
        if (change.type === "message") {
          // Handle incoming messages
          const msgData = change.data as Message;
          useAppStore.getState().addMessage(msgData.ameId, msgData);
        } else if (change.type === "ame_status") {
          const statusData = change.data as { id: string; status: AME["status"] };
          useAppStore.getState().updateAmeStatus(statusData.id, statusData.status);
        }
      }
    } catch (error) {
      console.error("Sync failed:", error);
      setSyncState({ isSyncing: false });
    }
  }, [sync.lastSync, isOfflineMode, setSyncState]);

  // Auto-sync every 30 seconds when app is active
  useEffect(() => {
    if (isOfflineMode) return;

    intervalRef.current = setInterval(performSync, 30000);

    const handleAppState = (state: AppStateStatus) => {
      if (state === "active") {
        performSync();
      }
    };

    const subscription = AppState.addEventListener("change", handleAppState);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      subscription.remove();
    };
  }, [performSync, isOfflineMode]);

  return { ...sync, performSync };
}

// Hook: Voice recording
export function useVoiceRecording() {
  const [isRecording, setIsRecording] = useState(false);
  const [audioUri, setAudioUri] = useState<string | null>(null);

  const startRecording = useCallback(async () => {
    try {
      // In a real app, use expo-av Audio.Recording
      setIsRecording(true);
      // TODO: Implement actual recording with expo-av
    } catch (error) {
      console.error("Failed to start recording:", error);
      Alert.alert("Error", "Failed to start recording");
    }
  }, []);

  const stopRecording = useCallback(async () => {
    try {
      setIsRecording(false);
      // TODO: Implement actual stop recording
    } catch (error) {
      console.error("Failed to stop recording:", error);
    }
  }, []);

  return { isRecording, audioUri, startRecording, stopRecording };
}

// Hook: Image picker
export function useImagePicker() {
  const [imageUri, setImageUri] = useState<string | null>(null);

  const pickImage = useCallback(async () => {
    try {
      // In a real app, use expo-image-picker
      // TODO: Implement actual image picking
    } catch (error) {
      console.error("Failed to pick image:", error);
      Alert.alert("Error", "Failed to pick image");
    }
  }, []);

  const clearImage = useCallback(() => {
    setImageUri(null);
  }, []);

  return { imageUri, pickImage, clearImage };
}