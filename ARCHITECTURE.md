# AURA/AME v3.0 — Architecture Overview

> Diagramas de arquitectura (Mermaid). La app web v3.0 está completa; las
> cajas marcadas "Phase 58" corresponden al trabajo futuro de Cline.

## System Diagram

```mermaid
graph TB
    subgraph Web["Web Application (Next.js)"]
        UI["Dashboard UI"]
        Integrations["Integrations Page"]
        Analytics["Analytics Dashboard"]
    end

    subgraph Backend["Vercel Serverless"]
        API["API Routes"]
        Webhooks["Webhook Manager"]
        Logger["Logger Service"]
    end

    subgraph External["External Services"]
        Slack["Slack API"]
        Discord["Discord API"]
        Telegram["Telegram API"]
        Teams["Teams API"]
    end

    subgraph Monitoring["Monitoring"]
        HealthCheck["Health Check"]
        Monitor["24/7 Monitor"]
        Logs["Log Storage"]
    end

    UI --> API
    Integrations --> API
    Analytics --> API
    API --> Webhooks
    API --> Logger
    Webhooks -->|HTTP POST| External
    Logger --> Logs
    HealthCheck --> Monitor

    style Web fill:#080408,color:#F0F0F8
    style Backend fill:#1a1a2e,color:#F0F0F8
    style External fill:#DC143C,color:#F0F0F8
    style Monitoring fill:#FFD700,color:#080408
```

## Data Flow (webhook trigger)

```mermaid
sequenceDiagram
    participant User
    participant Dashboard
    participant API
    participant WebhookMgr as Webhook Manager
    participant Target as External URL
    participant Logger

    User->>Dashboard: Crear webhook
    Dashboard->>API: POST /api/webhooks {url, events}
    API->>Logger: Log request
    API->>WebhookMgr: Register
    API-->>Dashboard: Success

    Note over User,Target: Más tarde, un evento se dispara
    User->>API: POST /api/webhooks {event, data}
    API->>Logger: Log request
    API->>WebhookMgr: Trigger(event)
    WebhookMgr->>Target: HTTP POST {event, data}
    Target-->>WebhookMgr: 200
    API-->>User: Success
```

## Component Hierarchy

```mermaid
graph TD
    App["AURA/AME App"]

    App --> Pages["Pages"]
    App --> Components["Components"]
    App --> Lib["Lib"]

    Pages --> Home["/ (Home)"]
    Pages --> Integrations["/integrations"]
    Pages --> Analytics["/analytics"]
    Pages --> AME["/ame"]

    Components --> IntCard["IntegrationCard"]
    Components --> StatusBadge["StatusBadge"]
    Components --> InstallButton["InstallButton"]
    Components --> ActivityLog["ActivityLog"]
    Components --> APIKeyDisplay["APIKeyDisplay"]
    Components --> ErrorBoundary["error.tsx"]

    Lib --> Logger["logger.js"]
    Lib --> FetchRetry["fetch-retry.ts"]
    Lib --> Auth["authenticate / requireAuth"]
    Lib --> RateLimit["rateLimit (ame-core)"]
```

## API Endpoints

```mermaid
graph LR
    API["/api"]

    API --> Health["health"]
    API --> Integrations["integrations/status"]
    API --> Webhooks["webhooks"]
    API --> Logs["logs"]
    API --> Slack["slack/install, slack/events"]
    API --> Discord["discord/webhook"]
    API --> Telegram["telegram/webhook"]
    API --> Teams["teams"]
    API --> AMECore["ame-core"]
```

## Security Layer

```mermaid
graph TD
    Request["Incoming Request"]

    Request --> CORS["CORS (next.config.js)"]
    CORS --> Auth["Authentication (API_SECRET_KEY)"]
    Auth --> Validate["Input Validation (SSRF guard)"]
    Validate --> Process["Process Request"]

    style CORS fill:#FFD700,color:#080408
    style Auth fill:#DC143C,color:#F0F0F8
    style Validate fill:#DC143C,color:#F0F0F8
```

> **Nota:** el rate limiting (`lib/rateLimit.ts`) está aplicado solo en
> `ame-core` en v3.0; ver `MEJORAS-FASE-57.md` para el plan de extenderlo.

## Deployment Architecture

```mermaid
graph TB
    subgraph Local["Local Development"]
        Dev["npm run dev"]
    end

    subgraph GitHub["GitHub"]
        Repo["Repository"]
        Actions["GitHub Actions (CI)"]
    end

    subgraph Vercel["Vercel Production"]
        Frontend["Next.js App"]
        Functions["Serverless Functions"]
    end

    subgraph Services["External Services"]
        Integrations["Slack/Discord/Telegram/Teams"]
    end

    Local --> Repo
    Repo --> Actions
    Actions --> Vercel
    Vercel --> Services
```
