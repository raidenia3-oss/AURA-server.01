# AURA/AME v2.0 — Asistente IA Empresarial

> Dashboard de integraciones empresariales para AME, con seguridad endurecida,
> monitoreo 24/7 y calidad de código verificable.

## Qué es

AURA/AME es un asistente IA con un dashboard web (Next.js App Router) que
conecta AME con las plataformas de tu equipo:

- 💬 **Slack** — comandos `/ame analyze`, `/ame news`
- 🎮 **Discord** — bot con comando `/ame`
- ✈️ **Telegram** — chat directo con el bot
- 👥 **Microsoft Teams** — app para equipos
- 🔗 **Webhooks Custom** — integración vía `POST /api/webhooks`

## Features

- 🎨 **Dashboard de integraciones** en `/integrations` (status dinámico,
  comandos, creación de webhooks, gestión de API key).
- 🔐 **Auth en APIs sensibles** (`/api/webhooks`, `/api/logs`) vía bearer
  `API_SECRET_KEY`.
- 🛡️ **Validación SSRF** en las URLs de webhook (bloquea loopback/privadas).
- ⚡ **Monitoreo 24/7** (`scripts/monitor-24-7.js`) con alertas automáticas.
- 📝 **Logging exhaustivo** (`lib/logger.js`) expuesto en `GET /api/logs`.
- 🔄 **Retry automático** con exponential backoff (`lib/fetch-retry.ts`).
- ⚠️ **Error boundary** + ⏳ **loading skeleton** en `/integrations`.

## Instalación

```bash
git clone https://github.com/raidenia3-oss/AURA-server.01.git
cd AURA-server.01/frontend
npm install
```

## Desarrollo local

El `package.json` fija `next` en una versión antigua para el entorno de
despliegue, pero el código usa APIs modernas de Next (App Router,
`next/server`). Por eso los comandos estándar `npm run lint` / `tsc` fallan
localmente. Usa en su lugar los scripts de verificación local:

```bash
npm run typecheck   # tsc -p tsconfig.local.json --noEmit (con shims)
npm run lint:local  # eslint -c eslint.local.mjs .
npm test            # node --test (logger, webhook-manager, smoke)
```

## Configuración (variables de entorno)

Crea `frontend/.env.local`:

```bash
# CORS: origen permitido para las rutas /api/*
NEXT_PUBLIC_SITE_URL=https://aura-web-chi-seven.vercel.app

# Bearer secret para /api/webhooks y /api/logs (si no está seteado, quedan abiertos en dev)
API_SECRET_KEY=tu_secret_key_aqui

# Integraciones (cada una enciende su status cuando está presente)
SLACK_CLIENT_ID=xoxb-...
SLACK_REDIRECT_URI=https://tu-app/api/slack/install
DISCORD_TOKEN=...
TELEGRAM_TOKEN=...
TEAMS_APP_ID=...

# Monitoreo 24/7
NEXT_PUBLIC_API_URL=https://aura-web-chi-seven.vercel.app
```

> **Nota de seguridad:** cuando `API_SECRET_KEY` NO está configurado,
> `/api/webhooks` y `/api/logs` quedan abiertos (modo dev). En producción
> define la variable para exigir el bearer token.

## Uso — Endpoints

| Método | Ruta                       | Auth | Descripción                          |
| ------ | -------------------------- | ---- | ------------------------------------ |
| GET    | `/api/health`              | No   | Health check global                  |
| GET    | `/api/integrations/status` | No   | Estado de cada integración           |
| GET    | `/api/logs`                | Sí*  | Log de eventos/errores               |
| GET    | `/api/webhooks`            | Sí*  | Lista webhooks                       |
| POST   | `/api/webhooks`            | Sí*  | Registra/dispara webhook             |
| DELETE | `/api/webhooks?id=<id>`    | Sí*  | Elimina webhook                      |
| GET    | `/api/slack/install`       | No   | OAuth install de Slack               |
| GET    | `/api/teams`               | No   | Info de la app Teams                 |

\* Requiere bearer `API_SECRET_KEY` solo cuando la variable está configurada.

## Seguridad

- ✅ **Webhooks protegidos** por API key (cuando `API_SECRET_KEY` está seteado).
- ✅ **Validación SSRF** en `/api/webhooks` (rechaza `localhost`, `127.0.0.1`,
  `0.0.0.0`, `::1`, `.local` y rangos `10.x` / `192.168.x` / `172.16-31.x` /
  `169.254.x`).
- ✅ **CORS** configurado en `next.config.js` para `/api/*`.
- ✅ **Logs protegidos** con el mismo bearer.
- ⚠️ **Rate limiting** implementado en `ame-core` (`lib/rateLimit.ts`); aún no
  está aplicado a las rutas de integraciones (ver `MEJORAS-FASE-57.md`).

## Testing

```bash
npm test          # node:test (logger + webhook-manager + smoke HTTP)
npm run typecheck # verificación de tipos local
npm run lint:local# lint local (parser @typescript-eslint)
```

Los smoke tests HTTP solo corren si defines `BASE_URL` (p.ej. contra un
despliegue vivo); se skipean localmente.

## Deployment

Despliegue automático en Vercel al hacer push a `main` (rootDirectory:
`frontend`).

```bash
git push origin main
# → Auto-deploy a https://aura-web-chi-seven.vercel.app
```

## Monitoreo

```bash
node scripts/monitor-24-7.js
```

Verifica `/api/health`, `/api/integrations/status`, `/api/webhooks` y
`/api/ame-core` cada 5 minutos y alerta si algo falla. El script no arranca
solo al importarse (solo con `require.main === module`).
