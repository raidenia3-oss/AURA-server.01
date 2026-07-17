import React, { useEffect, useState } from "react";
import { View, Text, ActivityIndicator, StyleSheet } from "react-native";
import { useAuth } from "./lib/hooks";
import { useAppStore } from "./lib/store";
import { initializeFirebase } from "./lib/firebase";
import LoginScreen from "./app/auth/LoginScreen";
import SignupScreen from "./app/auth/SignupScreen";
import ChatScreen from "./app/app/ChatScreen";
import AMEsListScreen from "./app/app/AMEsListScreen";
import SettingsScreen from "./app/app/SettingsScreen";

type Screen =
  | "loading"
  | "login"
  | "signup"
  | "amesList"
  | "chat"
  | "settings";

export default function App() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { loadPersistedState } = useAppStore();
  const [currentScreen, setCurrentScreen] = useState<Screen>("loading");
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const init = async () => {
      try {
        initializeFirebase();
        await loadPersistedState();
      } catch (error) {
        console.error("Init error:", error);
      } finally {
        setIsReady(true);
      }
    };
    init();
  }, [loadPersistedState]);

  useEffect(() => {
    if (!isReady || authLoading) {
      setCurrentScreen("loading");
    } else if (isAuthenticated) {
      setCurrentScreen("amesList");
    } else {
      setCurrentScreen("login");
    }
  }, [isReady, authLoading, isAuthenticated]);

  const renderScreen = () => {
    switch (currentScreen) {
      case "loading":
        return (
          <View style={styles.loadingContainer}>
            <Text style={styles.loadingTitle}>AURA</Text>
            <ActivityIndicator size="large" color="#00d4ff" />
            <Text style={styles.loadingText}>Initializing...</Text>
          </View>
        );

      case "login":
        return (
          <LoginScreen
            onNavigateSignup={() => setCurrentScreen("signup")}
            onForgotPassword={() => {}}
          />
        );

      case "signup":
        return (
          <SignupScreen
            onNavigateLogin={() => setCurrentScreen("login")}
          />
        );

      case "amesList":
        return (
          <View style={styles.appContainer}>
            <View style={styles.tabBar}>
              <Text
                style={styles.tabTitle}
                onPress={() => setCurrentScreen("amesList")}
              >
                AMEs
              </Text>
              <Text
                style={styles.tabTitle}
                onPress={() => setCurrentScreen("settings")}
              >
                Settings
              </Text>
            </View>
            <AMEsListScreen
              onSelectAme={() => setCurrentScreen("chat")}
            />
          </View>
        );

      case "chat":
        return (
          <View style={styles.appContainer}>
            <ChatScreen />
            <View style={styles.navBar}>
              <Text
                style={styles.navButton}
                onPress={() => setCurrentScreen("amesList")}
              >
                ← Back
              </Text>
            </View>
          </View>
        );

      case "settings":
        return (
          <View style={styles.appContainer}>
            <View style={styles.tabBar}>
              <Text
                style={styles.tabTitle}
                onPress={() => setCurrentScreen("amesList")}
              >
                AMEs
              </Text>
              <Text
                style={[styles.tabTitle, styles.tabTitleActive]}
                onPress={() => setCurrentScreen("settings")}
              >
                Settings
              </Text>
            </View>
            <SettingsScreen />
          </View>
        );

      default:
        return null;
    }
  };

  return <View style={styles.root}>{renderScreen()}</View>;
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#0a0a1a",
  },
  loadingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#0a0a1a",
  },
  loadingTitle: {
    fontSize: 48,
    fontWeight: "bold",
    color: "#00d4ff",
    letterSpacing: 6,
    marginBottom: 24,
  },
  loadingText: {
    color: "#888",
    fontSize: 16,
    marginTop: 16,
  },
  appContainer: {
    flex: 1,
  },
  tabBar: {
    flexDirection: "row",
    justifyContent: "space-around",
    backgroundColor: "#1a1a2e",
    paddingVertical: 12,
    paddingTop: 48,
    borderBottomWidth: 1,
    borderBottomColor: "#2a2a4e",
  },
  tabTitle: {
    color: "#888",
    fontSize: 16,
    fontWeight: "600",
  },
  tabTitleActive: {
    color: "#00d4ff",
  },
  navBar: {
    backgroundColor: "#1a1a2e",
    padding: 12,
    borderTopWidth: 1,
    borderTopColor: "#2a2a4e",
  },
  navButton: {
    color: "#00d4ff",
    fontSize: 16,
    fontWeight: "600",
  },
});