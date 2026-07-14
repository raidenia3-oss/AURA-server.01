"use client";

import { useState, useEffect } from "react";
import { palette } from "../../components/palette";
import IntegrationCard, {
  Integration,
} from "../../components/IntegrationCard";
import APIKeyDisplay from "../../components/APIKeyDisplay";
import ActivityLog, { ActivityEvent } from "../../components/ActivityLog";

interface StatusShape {
  slack: { connected: boolean; note: string };
  discord: { connected: boolean; note: string };
  telegram: { connected: boolean; note: string };
  teams: { connected: boolean; note: string };
  webhooks: { connected: boolean; count: number; note: string };
}

const integrations: Integration[] = [
  {
    name: "Slack",
    icon: "💬",
    description: "Usa AME directamente desde tus canales de Slack.",
    commands: ["/ame analyze", "/ame news"],
    installLabel: "Instalar",
    configureLabel: "Configurar",
    href: "/api/slack/install",
  },
  {
    name: "Discord",
    icon: "🎮",
    description: "Lleva el bot de AME a tus servidores de Discord.",
    commands: ["/ame"],
    installLabel: "Invitar Bot",
    configureLabel: "Configurar",
    href: "/api/discord/webhook",
  },
  {
    name: "Telegram",
    icon: "✈️",
    description: "Chat directo con AME desde Telegram.",
    commands: ["/start", "/help", "/ame"],
    installLabel: "Abrir Bot",
    configureLabel: "Configurar",
    href: "/api/telegram/webhook",
  },
  {
    name: "Microsoft Teams",
    icon: "👥",
    description: "Integra AME con los equipos de tu organización.",
    commands: ["/ame"],
    installLabel: "Agregar App",
    configureLabel: "Configurar",
    href: "/api/teams",
  },
  {
    name: "Webhooks Custom",
    icon: "🔗",
    description: "Conecta AME con cualquier servicio vía webhooks.",
    commands: ["POST /api/webhooks"],
    installLabel: "Crear Webhook",
    configureLabel: "Gestionar Webhooks",
    onClick: createWebhook,
  },
];

function createWebhook() {
  const url = window.prompt("URL del endpoint para el webhook:");
  if (!url) return;

  fetch("/api/webhooks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      id: `wh_${Date.now()}`,
      url,
      events: ["ame.event", "integration.message"],
    }),
  })
    .then((r) => r.json())
    .then((d) => {
      if (d.success) {
        window.alert("Webhook creado correctamente ✅");
        window.location.reload();
      } else {
        window.alert("No se pudo crear el webhook: " + JSON.stringify(d));
      }
    })
    .catch((e) => window.alert("Error: " + e.message));
}

export default function IntegrationsPage() {
  const [status, setStatus] = useState<StatusShape | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([
    {
      time: "hace 2 min",
      integration: "Slack",
      message: "Comando /ame analyze recibido",
      status: "success",
    },
    {
      time: "hace 15 min",
      integration: "Webhooks",
      message: "Evento ame.event procesado",
      status: "info",
    },
    {
      time: "hace 1 h",
      integration: "Telegram",
      message: "Conexión de bot verificada",
      status: "success",
    },
  ]);

  useEffect(() => {
    fetch("/api/integrations/status")
      .then((r) => r.json())
      .then((data: StatusShape) => setStatus(data))
      .catch(() => setStatus(null));
  }, []);

  const isConnected = (name: string): boolean => {
    if (!status) return false;
    if (name === "Webhooks Custom") return status.webhooks.connected;
    return Boolean(status[name.toLowerCase() as keyof StatusShape]?.connected);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background:
          "linear-gradient(135deg, #080408 0%, #1a1a2e 100%)",
        color: palette.text,
        padding: "40px 20px",
      }}
    >
      <div
        style={{
          marginBottom: "50px",
          paddingBottom: "20px",
          borderBottom: `2px solid ${palette.border}`,
        }}
      >
        <h1 style={{ fontSize: "36px", margin: "0 0 10px 0" }}>
          🔗 Integraciones Empresariales
        </h1>
        <p style={{ opacity: 0.7, margin: 0 }}>
          Conecta AME con tus plataformas favoritas
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
          gap: "25px",
          marginBottom: "50px",
        }}
      >
        {integrations.map((integration) => (
          <IntegrationCard
            key={integration.name}
            integration={integration}
            connected={isConnected(integration.name)}
          />
        ))}
      </div>

      <APIKeyDisplay />

      <div style={{ marginBottom: "30px" }}>
        <ActivityLog events={activity} />
      </div>

      <div
        style={{
          background: palette.cardBg,
          border: `2px solid ${palette.border}`,
          borderRadius: "12px",
          padding: "25px",
        }}
      >
        <h2 style={{ margin: "0 0 15px 0" }}>📚 Documentación</h2>
        <p style={{ margin: "0 0 10px 0", opacity: 0.8 }}>
          Consulta la referencia completa de la API y el formato de
          webhooks.
        </p>
        <a
          href="/docs/webhooks"
          style={{
            color: palette.accent,
            textDecoration: "none",
            fontWeight: 700,
          }}
        >
          API Reference →
        </a>
      </div>
    </div>
  );
}
