# AURA/AME - Sistema Autónomo de Noticias y Automatización

[![GitHub Release](https://img.shields.io/github/v/release/raidenia3-oss/AURA-server.01?style=flat-square&color=DC143C)](https://github.com/raidenia3-oss/AURA-server.01/releases)
[![GitHub Stars](https://img.shields.io/github/stars/raidenia3-oss/AURA-server.01?style=flat-square)](https://github.com/raidenia3-oss/AURA-server.01)
[![License](https://img.shields.io/github/license/raidenia3-oss/AURA-server.01?style=flat-square)](LICENSE)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue?style=flat-square)](https://www.typescriptlang.org/)
[![Tests](https://img.shields.io/badge/Tests-7%20Passed-brightgreen?style=flat-square)]()
[![Production Ready](https://img.shields.io/badge/Status-Production%20Ready-brightgreen?style=flat-square)]()

![AURA/AME Logo](https://via.placeholder.com/150x150?text=AURA+AME)

AURA/AME es un ecosistema integrado para gestión autónoma de noticias, automatización de tareas y experiencia de usuario mejorada con integraciones avanzadas.

---

## 🚀 Nuevas Características

### 1. **Integración con Google AI Studio**

- Análisis avanzado de noticias usando modelos de lenguaje de Google.
- Recomendaciones personalizadas basadas en intereses del usuario.
- Mejoras en el razonamiento de AURA para decisiones más precisas.
- **Modo Simulado**: Funciona con una clave de ejemplo para desarrollo local.

### 2. **Modo Sin JavaScript (Fallback)**

- Experiencia de usuario funcional incluso sin JavaScript.
- Avatar en ASCII art y noticias en formato de tabla HTML puro.
- Acceso a contenido esencial sin depender de scripts.

### 3. **Integración con Mini-Juegos (Godot)**

- Sistema de recompensas con EXP y monedas por completar juegos.
- Conexión WebSocket entre Godot y el backend de AURA.
- Plan de integración detallado en [docs/GAME_INTEGRATION.md](docs/GAME_INTEGRATION.md).

### 4. **GitHub Actions para Despliegue Automático**

- Despliegue automático en Vercel en cada commit a `main`.
- Pruebas automáticas y generación de changelogs.
- Versionamiento semántico automático.

---

## 📦 Instalación y Configuración

### Requisitos Previos

- Node.js (v20 o superior)
- npm o yarn
- Cuenta en Vercel para despliegue
- Google AI Studio API Key (opcional, para análisis avanzado)

### Instalación

```bash
git clone https://github.com/raidenia3-oss/AURA-server.01.git
cd AURA-server.01
cd frontend
npm install
```

### Configuración de Variables de Entorno

Crea un archivo `.env.local` en el directorio `frontend/` con el siguiente contenido:

```env
NEXT_PUBLIC_GOOGLE_AI_API_KEY=tu_api_key_real_de_google_ai_o_MOCK_API_KEY_FOR_TESTING
CRON_SECRET=tu_secreto_seguro
GEMINI_API_KEY=tu_api_key_real_de_gemini_o_MOCK_API_KEY_FOR_TESTING
NEXT_PUBLIC_FIREBASE_API_KEY=tu_api_key_real_de_firebase
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=tu_auth_domain_real_de_firebase
NEXT_PUBLIC_FIREBASE_PROJECT_ID=tu_project_id_real_de_firebase
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=tu_storage_bucket_real_de_firebase
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=tu_messaging_sender_id_real_de_firebase
NEXT_PUBLIC_FIREBASE_APP_ID=tu_app_id_real_de_firebase
NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID=tu_measurement_id_real_de_firebase
```

---

## 🔧 Arquitectura

### Frontend (Next.js)

- **Páginas principales**:
  - `/`: Página de inicio con noticias y recomendaciones.
  - `/ame`: Interfaz principal de AURA/AME.
  - `/ame-no-js.html`: Versión sin JavaScript para fallback.

- **Componentes clave**:
  - `lib/google-ai-studio.js`: Integración con Google AI para análisis de noticias (con modo simulado).
  - `components/SystemActions.jsx`: Historial de acciones del sistema.
  - `api/news-worker.js`: Endpoint para procesamiento de noticias.

### Backend (FastAPI)

- **Módulos principales**:
  - `agent_orchestrator.py`: Orquestador de agentes para automatización.
  - `news_worker.py`: Procesamiento de noticias y recomendaciones.
  - `event_bus.py`: Sistema de eventos para comunicación entre módulos.

### Automatización

- **Scripts**:
  - `scripts/install-browser-deps.sh`: Instalación de dependencias para automatización de navegadores.
  - `scripts/fix-vercel-final.sh`: Solución de problemas comunes en Vercel.
  - `scripts/setup-complete-fixed.cjs`: Configuración completa del entorno.

---

## 🎮 Integración con Mini-Juegos

### Descripción

AURA/AME ahora soporta la integración de mini-juegos desarrollados en Godot. Los usuarios pueden ganar experiencia (EXP) y recompensas al completar niveles, mejorando la interacción con la plataforma.

### Requisitos

- Godot Engine 4.x
- Proyecto Godot configurado para exportar a HTML5
- Cuenta en Vercel/Netlify para desplegar juegos

### Documentación

Consulta el documento [GAME_INTEGRATION.md](docs/GAME_INTEGRATION.md) para obtener detalles sobre cómo integrar tus juegos con AURA/AME.

---

## 🤖 Google AI Studio Integration

### Características

- Análisis avanzado de noticias con modelos de lenguaje de Google.
- Generación de resúmenes y recomendaciones personalizadas.
- Integración con el sistema de recomendaciones de AURA.
- **Modo Simulado**: Para desarrollo local sin API key real.

### Uso

```javascript
const GoogleAIStudio = require("./lib/google-ai-studio");
const aiStudio = new GoogleAIStudio(process.env.GOOGLE_AI_API_KEY);

async function analyzeNews() {
  const articleText = "Texto del artículo de noticias...";
  const userContext = "Interesado en tecnología, anime y automatización";

  const analysis = await aiStudio.analyzeArticle(articleText, userContext);
  console.log("Análisis:", analysis);

  const recommendations = await aiStudio.generateRecommendations([analysis]);
  console.log("Recomendaciones:", recommendations);
}
```

### Modo Simulado

Si no tienes una API key real de Google AI Studio, puedes usar el modo simulado que viene incluido por defecto. Simplemente usa la clave de ejemplo:

```env
NEXT_PUBLIC_GOOGLE_AI_API_KEY=MOCK_API_KEY_FOR_TESTING
```

El sistema generará respuestas simuladas para pruebas locales.

---

## 🌐 Despliegue en Vercel

### Configuración

Asegúrate de que tu `vercel.json` esté configurado correctamente:

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs"
}
```

### Despliegue

```bash
cd frontend
npm run build
vercel deploy --prod --force
```

### GitHub Actions

El proyecto incluye un flujo de trabajo automatizado para despliegue y pruebas:

- **Pruebas automáticas** en cada push o pull request.
- **Despliegue automático** a Vercel en cada commit a `main`.
- **Generación de releases** con changelog automático.

---

## 🔥 Configuración Manual de Firebase

Si el setup automático falla, puedes configurar Firebase manualmente:

1. **Obtén tus credenciales de Firebase:**
   - Ve a [Firebase Console](https://console.firebase.google.com/).
   - Selecciona tu proyecto "aura-ame-ecosystem".
   - Ve a **Project Settings** > **General**.
   - Copia la configuración de tu proyecto.

2. **Reemplaza los valores de ejemplo:**
   - Edita el archivo `frontend/.env.local` y reemplaza los valores de ejemplo con tus credenciales reales:
     ```env
     NEXT_PUBLIC_FIREBASE_API_KEY=tu_api_key_real
     NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=tu_auth_domain_real
     NEXT_PUBLIC_FIREBASE_PROJECT_ID=tu_project_id_real
     NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=tu_storage_bucket_real
     NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=tu_messaging_sender_id_real
     NEXT_PUBLIC_FIREBASE_APP_ID=tu_app_id_real
     NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID=tu_measurement_id_real
     ```

3. **Valida la configuración:**
   - Ejecuta el script de validación de Firebase para asegurarte de que todo funcione correctamente.

4. **Script de Configuración Manual:**
   - Ejecuta el siguiente script para configurar Firebase manualmente:
     ```bash
     node frontend/lib/firebase-setup-manual.js
     ```
   - Este script generará automáticamente el archivo `.env.local` con los valores de ejemplo y el script de inicialización de Firebase.

---

## 📚 Documentación Adicional

- [Guía de Modificación de AME](docs/ame_modification_guide.md)
- [Configuración Local de AI](docs/ai-local-setup.md)
- [Integración con Mini-Juegos](docs/GAME_INTEGRATION.md)
- [Chrome Extension Setup](docs/CHROME_EXTENSION_SETUP.md) _(próximamente)_

---

## 📈 Roadmap Futuro

### Primer Trimestre 2024

- [x] Integración con Google AI Studio (con modo simulado).
- [x] Modo sin JavaScript para fallback.
- [x] Documentación de integración con Godot.
- [x] GitHub Actions para despliegue automático.

### Segundo Trimestre 2024

- Implementar sistema de logros y badges.
- Competencias entre usuarios (leaderboards).
- Soporte para juegos multijugador en tiempo real.

### Tercer Trimestre 2024

- Sistema de economía virtual dentro de los juegos.
- Integración con más plataformas de juegos.
- Mejoras en el sistema de recomendaciones de noticias.

---

## 💡 Contribuyendo

¡Las contribuciones son bienvenidas! Por favor, abre un issue o envía un pull request.

### Cómo Contribuir

1. Haz un fork del repositorio.
2. Crea una rama para tu característica (`git checkout -b feature/nueva-caracteristica`).
3. Haz commit de tus cambios (`git commit -am 'Añadir nueva característica'`).
4. Haz push a la rama (`git push origin feature/nueva-caracteristica`).
5. Abre un Pull Request.

---

## 📧 Soporte

Para cualquier pregunta o problema, contacta al equipo de desarrollo en:

- **Email**: support@aura-ame.com
- **Documentación Técnica**: [docs.aura-ame.com](https://docs.aura-ame.com)

---

## 📜 Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.

---

## 📋 Guía Rápida para Desarrollo Local

### 1. Configuración Inicial

```bash
cd AURA-server.01
cd frontend
npm install
```

### 2. Iniciar Servidor de Desarrollo

```bash
npm run dev
```

### 3. Probar el Modo Simulado de Google AI Studio

```bash
node test-ai-studio-validation.js
```

### 4. Configurar Firebase Manualmente

```bash
node ../frontend/lib/firebase-setup-manual.js
```

### 5. Validar Configuración

- Abre [http://localhost:3000](http://localhost:3000) en tu navegador.
- Verifica que el avatar 3D cargue correctamente.
- Prueba la funcionalidad de la extensión de Chrome (si está instalada).

---

## 🔄 Solución de Problemas

### Problema: Google AI Studio no funciona

**Solución:**

1. Verifica que tengas una API key válida en `.env.local`.
2. Si usas el modo simulado, asegúrate de que la clave sea `MOCK_API_KEY_FOR_TESTING`.
3. Verifica tu conexión a internet.
4. Revisa los logs de consola para errores específicos.

### Problema: Firebase no se configura automáticamente

**Solución:**

1. Usa el script de configuración manual:
   ```bash
   node frontend/lib/firebase-setup-manual.js
   ```
2. Reemplaza los valores de ejemplo con tus credenciales reales.
3. Valida la configuración en tu aplicación.

### Problema: Chrome Extension no carga

**Solución:**

1. Verifica que todos los archivos estén presentes en la carpeta `chrome-extension-aura`.
2. Carga la extensión manualmente en Chrome:
   - Ve a `chrome://extensions/`.
   - Habilita el modo desarrollador.
   - Haz clic en "Cargar extensión no empaquetada".
   - Selecciona la carpeta `chrome-extension-aura`.

---

## 🎯 Próximos Pasos para el Desarrollo

1. **Implementar Chrome Extension**:
   - Completar la lógica en `background.js`.
   - Validar funcionalidad y generar documentación.

2. **Configurar EasyCron**:
   - Crear webhook para notificaciones.
   - Programar ejecución cada 6 horas.

3. **Realizar Tests End-to-End**:
   - Validar flujo completo de noticias y recomendaciones.
   - Probar integración con Google AI Studio (modo simulado o real).

4. **Crear Dashboard de Monitoreo**:
   - Diseñar interfaz para visualización de status.
   - Integrar APIs existentes.

---
