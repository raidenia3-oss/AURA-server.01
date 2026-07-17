import React, { useState, useRef, useEffect } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from "react-native";
import { useChat, useVoiceRecording, useImagePicker } from "../../lib/hooks";
import { useAppStore, Message } from "../../lib/store";

export default function ChatScreen() {
  const { selectedAmeId, ames } = useAppStore();
  const selectedAme = ames.find((a) => a.id === selectedAmeId);
  const { messages, isSending, error, sendMessage } = useChat(selectedAmeId);
  const { isRecording, startRecording, stopRecording } = useVoiceRecording();
  const { imageUri, pickImage, clearImage } = useImagePicker();
  const [inputText, setInputText] = useState("");
  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    if (messages.length > 0) {
      flatListRef.current?.scrollToEnd({ animated: true });
    }
  }, [messages]);

  const handleSend = () => {
    if (!inputText.trim() && !imageUri) return;
    sendMessage(inputText.trim(), imageUri || undefined);
    setInputText("");
    clearImage();
  };

  const renderMessage = ({ item }: { item: Message }) => {
    const isUser = item.role === "user";
    return (
      <View
        style={[
          styles.messageBubble,
          isUser ? styles.userBubble : styles.ameBubble,
        ]}
      >
        {item.imageUri && (
          <Text style={styles.messageImage}>[Image: {item.imageUri}]</Text>
        )}
        {item.audioUri && (
          <Text style={styles.messageAudio}>[Audio: {item.audioUri}]</Text>
        )}
        <Text style={[styles.messageText, isUser && styles.userMessageText]}>
          {item.content}
        </Text>
        <Text style={styles.messageTime}>
          {new Date(item.timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </Text>
      </View>
    );
  };

  if (!selectedAme) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyText}>Select an AME to start chatting</Text>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={Platform.OS === "ios" ? 90 : 0}
    >
      {/* Header */}
      <View style={styles.header}>
        <View
          style={[
            styles.statusDot,
            selectedAme.status === "online"
              ? styles.onlineDot
              : selectedAme.status === "busy"
              ? styles.busyDot
              : styles.offlineDot,
          ]}
        />
        <View>
          <Text style={styles.headerTitle}>{selectedAme.name}</Text>
          <Text style={styles.headerStatus}>{selectedAme.status}</Text>
        </View>
      </View>

      {/* Messages */}
      <FlatList
        ref={flatListRef}
        data={messages}
        renderItem={renderMessage}
        keyExtractor={(item) => item.id}
        style={styles.messageList}
        contentContainerStyle={styles.messageListContent}
        onContentSizeChange={() =>
          flatListRef.current?.scrollToEnd({ animated: true })
        }
      />

      {/* Error */}
      {error && (
        <View style={styles.errorBar}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}

      {/* Input */}
      <View style={styles.inputContainer}>
        <TouchableOpacity onPress={pickImage} style={styles.attachButton}>
          <Text style={styles.attachIcon}>📷</Text>
        </TouchableOpacity>

        <TouchableOpacity
          onPress={isRecording ? stopRecording : startRecording}
          style={[styles.attachButton, isRecording && styles.recordingButton]}
        >
          <Text style={styles.attachIcon}>
            {isRecording ? "⏹" : "🎤"}
          </Text>
        </TouchableOpacity>

        <TextInput
          style={styles.input}
          placeholder="Type a message..."
          placeholderTextColor="#666"
          value={inputText}
          onChangeText={setInputText}
          multiline
          maxLength={2000}
        />

        <TouchableOpacity
          onPress={handleSend}
          style={[
            styles.sendButton,
            (!inputText.trim() && !imageUri) && styles.sendButtonDisabled,
          ]}
          disabled={!inputText.trim() && !imageUri}
        >
          {isSending ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <Text style={styles.sendIcon}>➤</Text>
          )}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a1a",
  },
  emptyContainer: {
    flex: 1,
    backgroundColor: "#0a0a1a",
    justifyContent: "center",
    alignItems: "center",
  },
  emptyText: {
    color: "#666",
    fontSize: 16,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    padding: 16,
    backgroundColor: "#1a1a2e",
    borderBottomWidth: 1,
    borderBottomColor: "#2a2a4e",
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 12,
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
  headerTitle: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "bold",
  },
  headerStatus: {
    color: "#888",
    fontSize: 12,
    textTransform: "capitalize",
  },
  messageList: {
    flex: 1,
  },
  messageListContent: {
    padding: 16,
  },
  messageBubble: {
    maxWidth: "80%",
    padding: 12,
    borderRadius: 16,
    marginBottom: 8,
  },
  userBubble: {
    backgroundColor: "#00d4ff",
    alignSelf: "flex-end",
    borderBottomRightRadius: 4,
  },
  ameBubble: {
    backgroundColor: "#1a1a2e",
    alignSelf: "flex-start",
    borderBottomLeftRadius: 4,
  },
  messageText: {
    color: "#fff",
    fontSize: 16,
    lineHeight: 22,
  },
  userMessageText: {
    color: "#0a0a1a",
  },
  messageImage: {
    color: "#888",
    fontSize: 12,
    marginBottom: 4,
  },
  messageAudio: {
    color: "#888",
    fontSize: 12,
    marginBottom: 4,
  },
  messageTime: {
    color: "rgba(255,255,255,0.5)",
    fontSize: 11,
    marginTop: 4,
    alignSelf: "flex-end",
  },
  errorBar: {
    backgroundColor: "#ff4444",
    padding: 8,
    alignItems: "center",
  },
  errorText: {
    color: "#fff",
    fontSize: 12,
  },
  inputContainer: {
    flexDirection: "row",
    alignItems: "center",
    padding: 12,
    backgroundColor: "#1a1a2e",
    borderTopWidth: 1,
    borderTopColor: "#2a2a4e",
  },
  attachButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "#2a2a4e",
    justifyContent: "center",
    alignItems: "center",
    marginRight: 8,
  },
  recordingButton: {
    backgroundColor: "#ff4444",
  },
  attachIcon: {
    fontSize: 18,
  },
  input: {
    flex: 1,
    backgroundColor: "#0a0a1a",
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    color: "#fff",
    fontSize: 16,
    maxHeight: 100,
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "#00d4ff",
    justifyContent: "center",
    alignItems: "center",
    marginLeft: 8,
  },
  sendButtonDisabled: {
    opacity: 0.4,
  },
  sendIcon: {
    fontSize: 18,
    color: "#0a0a1a",
  },
});