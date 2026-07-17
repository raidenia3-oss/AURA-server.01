import { create } from "zustand";
import AsyncStorage from "@react-native-async-storage/async-storage";

// Types
export interface AME {
  id: string;
  name: string;
  status: "online" | "offline" | "busy";
  lastActivity: string;
  unreadCount: number;
}

export interface Message {
  id: string;
  ameId: string;
  role: "user" | "ame";
  content: string;
  timestamp: string;
  imageUri?: string;
  audioUri?: string;
}

export interface SyncState {
  lastSync: string | null;
  isSyncing: boolean;
  pendingChanges: number;
}

interface AppState {
  // Auth
  isAuthenticated: boolean;
  userEmail: string | null;
  authToken: string | null;

  // AMEs
  ames: AME[];
  selectedAmeId: string | null;

  // Messages
  messages: Record<string, Message[]>;

  // Sync
  sync: SyncState;

  // UI
  isOfflineMode: boolean;
  theme: "light" | "dark";
  language: string;

  // Actions
  setAuth: (email: string, token: string) => void;
  clearAuth: () => void;
  setAmes: (ames: AME[]) => void;
  selectAme: (ameId: string) => void;
  addMessage: (ameId: string, message: Message) => void;
  setMessages: (ameId: string, messages: Message[]) => void;
  setOfflineMode: (enabled: boolean) => void;
  setTheme: (theme: "light" | "dark") => void;
  setLanguage: (lang: string) => void;
  setSyncState: (state: Partial<SyncState>) => void;
  updateAmeStatus: (ameId: string, status: AME["status"]) => void;
  incrementUnread: (ameId: string) => void;
  clearUnread: (ameId: string) => void;

  // Persistence
  persistState: () => Promise<void>;
  loadPersistedState: () => Promise<void>;
}

const STORAGE_KEY = "ame-app-state";

export const useAppStore = create<AppState>((set, get) => ({
  // Initial state
  isAuthenticated: false,
  userEmail: null,
  authToken: null,
  ames: [],
  selectedAmeId: null,
  messages: {},
  sync: {
    lastSync: null,
    isSyncing: false,
    pendingChanges: 0,
  },
  isOfflineMode: false,
  theme: "light",
  language: "en",

  // Auth actions
  setAuth: (email: string, token: string) =>
    set({ isAuthenticated: true, userEmail: email, authToken: token }),

  clearAuth: () =>
    set({
      isAuthenticated: false,
      userEmail: null,
      authToken: null,
      ames: [],
      selectedAmeId: null,
      messages: {},
    }),

  // AME actions
  setAmes: (ames: AME[]) => set({ ames }),

  selectAme: (ameId: string) => set({ selectedAmeId: ameId }),

  updateAmeStatus: (ameId: string, status: AME["status"]) =>
    set((state) => ({
      ames: state.ames.map((ame) =>
        ame.id === ameId ? { ...ame, status } : ame
      ),
    })),

  incrementUnread: (ameId: string) =>
    set((state) => ({
      ames: state.ames.map((ame) =>
        ame.id === ameId
          ? { ...ame, unreadCount: ame.unreadCount + 1 }
          : ame
      ),
    })),

  clearUnread: (ameId: string) =>
    set((state) => ({
      ames: state.ames.map((ame) =>
        ame.id === ameId ? { ...ame, unreadCount: 0 } : ame
      ),
    })),

  // Message actions
  addMessage: (ameId: string, message: Message) =>
    set((state) => ({
      messages: {
        ...state.messages,
        [ameId]: [...(state.messages[ameId] || []), message],
      },
    })),

  setMessages: (ameId: string, messages: Message[]) =>
    set((state) => ({
      messages: { ...state.messages, [ameId]: messages },
    })),

  // UI actions
  setOfflineMode: (enabled: boolean) => set({ isOfflineMode: enabled }),
  setTheme: (theme: "light" | "dark") => set({ theme }),
  setLanguage: (lang: string) => set({ language: lang }),

  // Sync actions
  setSyncState: (state: Partial<SyncState>) =>
    set((prev) => ({ sync: { ...prev.sync, ...state } })),

  // Persistence
  persistState: async () => {
    try {
      const state = get();
      const data = JSON.stringify({
        isAuthenticated: state.isAuthenticated,
        userEmail: state.userEmail,
        authToken: state.authToken,
        ames: state.ames,
        messages: state.messages,
        sync: state.sync,
        isOfflineMode: state.isOfflineMode,
        theme: state.theme,
        language: state.language,
      });
      await AsyncStorage.setItem(STORAGE_KEY, data);
    } catch (error) {
      console.error("Failed to persist state:", error);
    }
  },

  loadPersistedState: async () => {
    try {
      const data = await AsyncStorage.getItem(STORAGE_KEY);
      if (data) {
        const parsed = JSON.parse(data);
        set({
          isAuthenticated: parsed.isAuthenticated || false,
          userEmail: parsed.userEmail || null,
          authToken: parsed.authToken || null,
          ames: parsed.ames || [],
          messages: parsed.messages || {},
          sync: parsed.sync || { lastSync: null, isSyncing: false, pendingChanges: 0 },
          isOfflineMode: parsed.isOfflineMode || false,
          theme: parsed.theme || "light",
          language: parsed.language || "en",
        });
      }
    } catch (error) {
      console.error("Failed to load persisted state:", error);
    }
  },
}));