"use client";
import { use, useState, useEffect } from "react";
import { autoLearningEngine } from "@/lib/auto-learning-engine";

export default function AMEDetail({
  params,
}: {
  params: Promise<{ ameId: string }>;
}) {
  const { ameId } = use(params);
  const [offline, setOffline] = useState(
    typeof window !== "undefined" && !navigator.onLine,
  );

  useEffect(() => {
    const handleOnline = () => setOffline(false);
    const handleOffline = () => setOffline(true);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  useEffect(() => {
    autoLearningEngine.startAutoEvolution(30);
    autoLearningEngine.recordInteraction({
      type: "ame_open",
      success: true,
      duration: 0,
      outcome: "AME abierto",
    });
  }, []);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #080408 0%, #1a1a2e 100%)",
        color: "#F0F0F8",
        padding: "20px",
        fontFamily: "Arial, sans-serif",
      }}
    >
      <button
        onClick={() => (window.location.href = "/ame")}
        style={{
          background: "#DC143C",
          color: "#F0F0F8",
          border: "none",
          padding: "10px 20px",
          borderRadius: "4px",
          cursor: "pointer",
          marginBottom: "20px",
        }}
      >
        ← Atrás
      </button>

      {offline && (
        <div
          style={{
            padding: "10px",
            background: "#FFD700",
            color: "#080408",
            borderRadius: "4px",
            marginBottom: "20px",
            fontWeight: "bold",
          }}
        >
          📱 Modo offline
        </div>
      )}

      <div
        style={{
          width: "120px",
          height: "120px",
          background: "#1a1a2e",
          border: "3px solid #FFD700",
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "60px",
          margin: "20px 0",
        }}
      >
        🤖
      </div>

      <h1 style={{ fontSize: "28px", margin: "0 0 10px 0" }}>AME {ameId}</h1>
      <p style={{ margin: "0 0 20px 0" }}>
        Estado: <span style={{ color: "#FFD700" }}>● Activo</span>
      </p>

      <div
        style={{
          background: "#1a1a2e",
          border: "1px solid #DC143C",
          borderRadius: "8px",
          padding: "20px",
          marginTop: "20px",
          minHeight: "300px",
        }}
      >
        <h3 style={{ margin: "0 0 15px 0" }}>Chat en tiempo real</h3>
        <div
          style={{
            background: "#080408",
            padding: "15px",
            borderRadius: "4px",
            marginTop: "10px",
            minHeight: "200px",
          }}
        >
          <p style={{ opacity: 0.7 }}>Chat aquí...</p>
        </div>
        <input
          type="text"
          placeholder="Escribe tu mensaje..."
          style={{
            width: "100%",
            padding: "10px",
            marginTop: "10px",
            background: "#080408",
            color: "#F0F0F8",
            border: "1px solid #DC143C",
            borderRadius: "4px",
            boxSizing: "border-box",
          }}
        />
      </div>
    </div>
  );
}
