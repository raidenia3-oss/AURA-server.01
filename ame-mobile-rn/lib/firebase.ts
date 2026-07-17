import { initializeApp, FirebaseApp } from "firebase/app";
import {
  getAuth,
  Auth,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  User,
  sendPasswordResetEmail,
} from "firebase/auth";

// Firebase configuration from environment variables
const firebaseConfig = {
  apiKey: process.env.EXPO_PUBLIC_FIREBASE_API_KEY || "",
  authDomain: process.env.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN || "",
  projectId: process.env.EXPO_PUBLIC_FIREBASE_PROJECT_ID || "",
  storageBucket: process.env.EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET || "",
  messagingSenderId: process.env.EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "",
  appId: process.env.EXPO_PUBLIC_FIREBASE_APP_ID || "",
};

let app: FirebaseApp | null = null;
let auth: Auth | null = null;

export function initializeFirebase(): void {
  if (!app) {
    app = initializeApp(firebaseConfig);
    auth = getAuth(app);
  }
}

export function getFirebaseAuth(): Auth {
  if (!auth) {
    initializeFirebase();
  }
  if (!auth) throw new Error("Firebase Auth not initialized");
  return auth;
}

// Auth API
export async function loginWithEmail(
  email: string,
  password: string
): Promise<User> {
  const authInstance = getFirebaseAuth();
  const result = await signInWithEmailAndPassword(authInstance, email, password);
  return result.user;
}

export async function signupWithEmail(
  email: string,
  password: string
): Promise<User> {
  const authInstance = getFirebaseAuth();
  const result = await createUserWithEmailAndPassword(
    authInstance,
    email,
    password
  );
  return result.user;
}

export async function logout(): Promise<void> {
  const authInstance = getFirebaseAuth();
  await signOut(authInstance);
}

export async function resetPassword(email: string): Promise<void> {
  const authInstance = getFirebaseAuth();
  await sendPasswordResetEmail(authInstance, email);
}

export function onAuthChange(callback: (user: User | null) => void): () => void {
  const authInstance = getFirebaseAuth();
  const unsubscribe = onAuthStateChanged(authInstance, callback);
  return unsubscribe;
}

export async function getAuthToken(): Promise<string | null> {
  const authInstance = getFirebaseAuth();
  const user = authInstance.currentUser;
  if (!user) return null;
  const token = await user.getIdToken();
  return token;
}