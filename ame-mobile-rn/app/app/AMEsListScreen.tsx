import React, { useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
} from "react-native";
import { useAmes } from "../../lib/hooks";
import { useAppStore, AME } from "../../lib/store";

interface AMEsListScreenProps {
  onSelectAme: (ameId: string) => void;
}

export default function AMEsListScreen({ onSelectAme }: AMEsListScreenProps) {
  const { ames, isLoading, error, refresh } = useAmes();
  const { selectAme } = useAppStore();

  const handleSelectAme = useCallback(
    (ame: AME) => {
      selectAme(ame.id);
      onSelectAme(ame.id);
    },
    [selectAme, onSelectAme]
  );

  const renderAmeItem = ({ item }: { item: AME }) => (
    <TouchableOpacity
      style={styles.ameItem}
      onPress={() => handleSelectAme(item)}
      activeOpacity={0.7}
    >
      <View style={styles.ameHeader}>
        <View style={styles.ameInfo}>
          <View
            style={[
              styles.statusDot,
              item.status === "online"
                ? styles.onlineDot
                : item.status === "busy"
                ? styles.busyDot
                : styles.offlineDot,
            ]}
          />
          <Text style={styles.ameName}>{item.name}</Text>
        </View>
        {item.unreadCount > 0 && (
          <View style={styles.unreadBadge}>
            <Text style={styles.unreadText}>
              {item.unreadCount > 99 ? "99+" : item.unreadCount}
            </Text>
          </View>
        )}
      </View>
      <Text style={styles.ameStatus}>{item.status}</Text>
      <Text style={styles.ameTime}>
        Last active: {new Date(item.lastActivity).toLocaleString()}
      </Text>
    </TouchableOpacity>
  );

  if (isLoading && ames.length === 0) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#00d4ff" />
        <Text style={styles.loadingText}>Loading AMEs...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={refresh}>
          <Text style={styles.retryText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.sectionTitle}>Your AMEs</Text>
      <FlatList
        data={ames}
        renderItem={renderAmeItem}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={isLoading}
            onRefresh={refresh}
            tintColor="#00d4ff"
          />
        }
        ListEmptyComponent={
          <View style={styles.centered}>
            <Text style={styles.emptyText}>No AMEs found</Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a1a",
  },
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#0a0a1a",
    padding: 24,
  },
  sectionTitle: {
    fontSize: 24,
    fontWeight: "bold",
    color: "#fff",
    padding: 16,
    paddingBottom: 8,
  },
  listContent: {
    padding: 16,
    paddingTop: 8,
  },
  ameItem: {
    backgroundColor: "#1a1a2e",
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "#2a2a4e",
  },
  ameHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  ameInfo: {
    flexDirection: "row",
    alignItems: "center",
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  onlineDot: {
    backgroundColor: "#00ff88",
  },
  busyDot: {
    backgroundColor: "#ffaa00",
  },
  offlineDot: {
    backgroundColor: "#666",
  },
  ameName: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "600",
  },
  unreadBadge: {
    backgroundColor: "#00d4ff",
    borderRadius: 12,
    minWidth: 24,
    height: 24,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 6,
  },
  unreadText: {
    color: "#0a0a1a",
    fontSize: 12,
    fontWeight: "bold",
  },
  ameStatus: {
    color: "#888",
    fontSize: 14,
    textTransform: "capitalize",
    marginBottom: 4,
  },
  ameTime: {
    color: "#666",
    fontSize: 12,
  },
  loadingText: {
    color: "#888",
    fontSize: 16,
    marginTop: 12,
  },
  errorText: {
    color: "#ff4444",
    fontSize: 16,
    textAlign: "center",
    marginBottom: 16,
  },
  retryButton: {
    backgroundColor: "#00d4ff",
    borderRadius: 8,
    padding: 12,
    paddingHorizontal: 24,
  },
  retryText: {
    color: "#0a0a1a",
    fontSize: 16,
    fontWeight: "bold",
  },
  emptyText: {
    color: "#666",
    fontSize: 16,
    textAlign: "center",
    marginTop: 48,
  },
});