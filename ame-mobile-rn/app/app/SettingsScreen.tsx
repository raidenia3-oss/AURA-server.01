import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Switch,
  Alert,
} from "react-native";
import { useAuth, useSync } from "../../lib/hooks";
import { useAppStore } from "../../lib/store";

export default function SettingsScreen() {
  const { userEmail, logout } = useAuth();
  const { lastSync, isSyncing, pendingChanges, performSync } = useSync();
  const {
    isOfflineMode,
    theme,
    language,
    setOfflineMode,
    setTheme,
    setLanguage,
  } = useAppStore();

  const handleLogout = () => {
    Alert.alert("Logout", "Are you sure you want to logout?", [
      { text: "Cancel", style: "cancel" },
      { text: "Logout", style: "destructive", onPress: logout },
    ]);
  };

  return (
    <ScrollView style={styles.container}>
      {/* Account Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Account</Text>
        <View style={styles.card}>
          <View style={styles.row}>
            <Text style={styles.label}>Email</Text>
            <Text style={styles.value}>{userEmail || "Not signed in"}</Text>
          </View>
        </View>
      </View>

      {/* Sync Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Sync</Text>
        <View style={styles.card}>
          <View style={styles.row}>
            <Text style={styles.label}>Last Sync</Text>
            <Text style={styles.value}>
              {lastSync
                ? new Date(lastSync).toLocaleString()
                : "Never"}
            </Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Pending Changes</Text>
            <Text style={styles.value}>{pendingChanges}</Text>
          </View>
          <TouchableOpacity
            style={[styles.syncButton, isSyncing && styles.syncButtonDisabled]}
            onPress={performSync}
            disabled={isSyncing}
          >
            <Text style={styles.syncButtonText}>
              {isSyncing ? "Syncing..." : "Sync Now"}
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Preferences Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Preferences</Text>
        <View style={styles.card}>
          <View style={styles.row}>
            <Text style={styles.label}>Offline Mode</Text>
            <Switch
              value={isOfflineMode}
              onValueChange={setOfflineMode}
              trackColor={{ false: "#2a2a4e", true: "#00d4ff" }}
              thumbColor={isOfflineMode ? "#fff" : "#888"}
            />
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Theme</Text>
            <View style={styles.themeButtons}>
              <TouchableOpacity
                style={[
                  styles.themeButton,
                  theme === "light" && styles.themeButtonActive,
                ]}
                onPress={() => setTheme("light")}
              >
                <Text
                  style={[
                    styles.themeButtonText,
                    theme === "light" && styles.themeButtonTextActive,
                  ]}
                >
                  Light
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.themeButton,
                  theme === "dark" && styles.themeButtonActive,
                ]}
                onPress={() => setTheme("dark")}
              >
                <Text
                  style={[
                    styles.themeButtonText,
                    theme === "dark" && styles.themeButtonTextActive,
                  ]}
                >
                  Dark
                </Text>
              </TouchableOpacity>
            </View>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Language</Text>
            <TouchableOpacity
              style={styles.languageButton}
              onPress={() => {
                const langs = ["en", "es", "fr", "de", "pt"];
                const currentIndex = langs.indexOf(language);
                const nextLang = langs[(currentIndex + 1) % langs.length];
                setLanguage(nextLang);
              }}
            >
              <Text style={styles.languageText}>{language.toUpperCase()}</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>

      {/* About Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About</Text>
        <View style={styles.card}>
          <View style={styles.row}>
            <Text style={styles.label}>Version</Text>
            <Text style={styles.value}>4.0.0</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Build</Text>
            <Text style={styles.value}>Phase 58</Text>
          </View>
        </View>
      </View>

      {/* Logout */}
      <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
        <Text style={styles.logoutText}>Sign Out</Text>
      </TouchableOpacity>

      <View style={styles.footer} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a1a",
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: "600",
    color: "#888",
    textTransform: "uppercase",
    letterSpacing: 1,
    paddingHorizontal: 16,
    paddingBottom: 8,
    paddingTop: 16,
  },
  card: {
    backgroundColor: "#1a1a2e",
    borderRadius: 12,
    marginHorizontal: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: "#2a2a4e",
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#2a2a4e",
  },
  label: {
    color: "#fff",
    fontSize: 16,
  },
  value: {
    color: "#888",
    fontSize: 14,
  },
  syncButton: {
    backgroundColor: "#00d4ff",
    borderRadius: 8,
    padding: 12,
    alignItems: "center",
    marginTop: 12,
  },
  syncButtonDisabled: {
    opacity: 0.6,
  },
  syncButtonText: {
    color: "#0a0a1a",
    fontSize: 16,
    fontWeight: "bold",
  },
  themeButtons: {
    flexDirection: "row",
    gap: 8,
  },
  themeButton: {
    backgroundColor: "#2a2a4e",
    borderRadius: 8,
    padding: 8,
    paddingHorizontal: 16,
  },
  themeButtonActive: {
    backgroundColor: "#00d4ff",
  },
  themeButtonText: {
    color: "#888",
    fontSize: 14,
  },
  themeButtonTextActive: {
    color: "#0a0a1a",
    fontWeight: "bold",
  },
  languageButton: {
    backgroundColor: "#2a2a4e",
    borderRadius: 8,
    padding: 8,
    paddingHorizontal: 16,
  },
  languageText: {
    color: "#00d4ff",
    fontSize: 14,
    fontWeight: "bold",
  },
  logoutButton: {
    backgroundColor: "#ff4444",
    borderRadius: 12,
    padding: 16,
    alignItems: "center",
    marginHorizontal: 16,
    marginTop: 8,
  },
  logoutText: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "bold",
  },
  footer: {
    height: 48,
  },
});