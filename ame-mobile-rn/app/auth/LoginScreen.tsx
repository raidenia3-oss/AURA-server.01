import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { loginWithEmail, resetPassword } from "../../lib/firebase";

interface LoginScreenProps {
  onNavigateSignup: () => void;
  onForgotPassword: () => void;
}

export default function LoginScreen({
  onNavigateSignup,
  onForgotPassword,
}: LoginScreenProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert("Error", "Please fill in all fields");
      return;
    }

    setIsLoading(true);
    try {
      await loginWithEmail(email.trim(), password);
      // Auth state listener in useAuth hook will handle navigation
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : "Login failed";
      Alert.alert("Login Failed", message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPassword = async () => {
    if (!email.trim()) {
      Alert.alert("Error", "Please enter your email first");
      return;
    }
    try {
      await resetPassword(email.trim());
      Alert.alert("Success", "Password reset email sent");
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : "Failed to send reset email";
      Alert.alert("Error", message);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <View style={styles.header}>
        <Text style={styles.title}>AURA</Text>
        <Text style={styles.subtitle}>Sign in to continue</Text>
      </View>

      <View style={styles.form}>
        <TextInput
          style={styles.input}
          placeholder="Email"
          placeholderTextColor="#666"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
          autoCorrect={false}
        />

        <TextInput
          style={styles.input}
          placeholder="Password"
          placeholderTextColor="#666"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <TouchableOpacity
          style={[styles.button, isLoading && styles.buttonDisabled]}
          onPress={handleLogin}
          disabled={isLoading}
        >
          {isLoading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Sign In</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity onPress={handleResetPassword} style={styles.linkButton}>
          <Text style={styles.linkText}>Forgot Password?</Text>
        </TouchableOpacity>

        <TouchableOpacity onPress={onNavigateSignup} style={styles.linkButton}>
          <Text style={styles.linkText}>
            Don't have an account? <Text style={styles.linkBold}>Sign Up</Text>
          </Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a1a",
    justifyContent: "center",
    padding: 24,
  },
  header: {
    alignItems: "center",
    marginBottom: 48,
  },
  title: {
    fontSize: 42,
    fontWeight: "bold",
    color: "#00d4ff",
    letterSpacing: 4,
  },
  subtitle: {
    fontSize: 16,
    color: "#888",
    marginTop: 8,
  },
  form: {
    width: "100%",
  },
  input: {
    backgroundColor: "#1a1a2e",
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    color: "#fff",
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "#2a2a4e",
  },
  button: {
    backgroundColor: "#00d4ff",
    borderRadius: 12,
    padding: 16,
    alignItems: "center",
    marginTop: 8,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: "#0a0a1a",
    fontSize: 18,
    fontWeight: "bold",
  },
  linkButton: {
    alignItems: "center",
    marginTop: 16,
  },
  linkText: {
    color: "#888",
    fontSize: 14,
  },
  linkBold: {
    color: "#00d4ff",
    fontWeight: "bold",
  },
});