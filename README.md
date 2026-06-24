# 🌐 **AURA/AME — Sistema Operativo Distribuido**
> **Red autónoma de nodos AURA (PC) + AME (Android)**

![AURA/AME Architecture](https://raw.githubusercontent.com/raidenia3-oss/AURA-server.01/main/docs/aura_ame_architecture.png)

---

## 🚀 **Iniciar Rápido**

### **1. Configuración Inicial (PC)**
```bash
# Clonar repositorio
git clone https://github.com/TU_USUARIO/aura-ame.git
cd aura-ame

# Instalar dependencias
pip install -r requirements.txt

# Configurar Cloudflare Tunnel (gratis)
python scripts/setup_cloudflare.py  # Selecciona opción [1] para trycloudflare.com

# Iniciar todo
python scripts/start_aura.py
```

### **2. Configuración en Android (Termux)**
```bash
# Copiar config a /sdcard/
adb push aura_urls/ame_config.json /sdcard/

# Verificar conexión
python scripts/test_ame_connection.py
```

---

## 🔧 **Verificación del Sistema**

### **Verificar salud del sistema (PC)**
```bash
python scripts/health_check.py
```
**Salida esperada:**
```
🎉 ¡Sistema listo para operar!
```

### **Verificar conexión desde Android**
```bash
# En Termux (Android)
python scripts/test_ame_connection.py
```
**Salida esperada:**
```
🎉 ¡Conexión exitosa! AME puede comunicarse con AURA Core
```

---

## 🔄 **Actualizaciones Automáticas**

### **Actualizar AURA Core (PC)**
```bash
# Ejecutar en segundo plano (revisa cada hora)
python scripts/auto_updater.py
```

### **Actualizar AME (Android)**
```bash
# Ejecutar en Termux (revisa cada 6 horas)
python scripts/ame_updater.py
```

---

## 📋 **Estructura del Proyecto**

```
aura-ame/
├── AURA_Core/                # Backend principal (Python)
│   ├── nodes/                # Nodos de automatización
│   │   └── NOD_ROLLERCOIN_BOT.py
│   ├── aura_core.py          # Núcleo del sistema
│   └── ...
├── AME_Core/                 # Frontend móvil (Python/JS)
├── godot_game/               # Juego en Godot 4.x
├── scripts/                  # Scripts de utilidad
│   ├── setup_cloudflare.py   # Configura túnel Cloudflare
│   ├── start_aura.py         # Inicia todos los servicios
│   ├── health_check.py       # Verifica estado del sistema
│   ├── auto_updater.py       # Actualizador automático (PC)
│   └── ame_updater.py        # Actualizador automático (Android)
├── tests/                    # Tests automatizados
│   └── test_core.py
├── .github/workflows/        # GitHub Actions (gratis)
│   ├── test.yml              # Tests en cada push
│   └── notify.yml            # Notificaciones de releases
├── version.json              # Versiones de todos los componentes
├── CHANGELOG.md              # Registro de cambios
├── requirements.txt          # Dependencias Python
└── README.md                 # Este archivo
```

---

## 🔐 **Seguridad**

✅ **Todo gratuito**:
- GitHub (gratis)
- GitHub Actions (2000 min/mes gratis)
- Cloudflare Tunnel (trycloudflare.com gratis, sin tarjeta)

✅ **Sin servicios de pago**:
- Sin Docker
- Sin AWS/GCP/Azure
- Sin contenedores

✅ **Protecciones**:
- `.gitignore` completo (no sube credenciales)
- `aura_urls.json` no se sube a GitHub
- `ame_config.json` solo se usa localmente

---

## 📱 **Requisitos**

### **PC (AURA Core)**
- Python 3.11+
- Git instalado
- Cloudflare Tunnel (se instala automáticamente)
- trycloudflare.com (gratis, sin cuenta)

### **Android (AME)**
- Termux instalado
- Python 3.10+ en Termux
- Permisos de escritura en `/sdcard/`
- Conexión a internet

---

## 🔧 **Desarrollo**

### **Añadir un nuevo nodo**
1. Crea un archivo en `AURA_Core/nodes/NOD_NUEVO.py`
2. Implementa la lógica de automatización
3. Añade el nodo a `nodes_config.json`

### **Actualizar versión**
```bash
# Incrementar versión (ej: patch)
python scripts/version_manager.py bump --component aura_core

# Añadir cambios al changelog
python scripts/version_manager.py bump --component aura_core --changes "Nueva funcionalidad" "Arreglo de bug"
```

### **Ejecutar tests**
```bash
# Tests locales
python -m pytest tests/test_core.py -v

# Tests en GitHub Actions (automático)
# Se ejecuta en cada push a main
```

---

## 🎮 **Ejemplo: Nodo Rollercoin Bot**
```python
# AURA_Core/nodes/NOD_ROLLERCOIN_BOT.py
from playwright.async_api import async_playwright

async def play_coin_flip_game(page):
    """Juega el juego de la moneda automáticamente"""
    await page.click(".heads")  # O ".tails" aleatoriamente
    await page.wait_for_selector(".points-gained")
    return await page.inner_text(".points-gained")
```

---

## 📡 **Conexión entre AURA y AME**

```
AME (Android/Termux)
    → ws://localhost:8765 (EventBus)
    ↓ Cloudflare Tunnel (trycloudflare.com)
AURA Core (PC)
    ← godot_bridge.py (puerto 9090)
    ← event_bus.py (puerto 8765)
```

---

## 🔄 **Flujo de Actualizaciones**

1. **Desarrollo en PC**:
   ```bash
   git add .
   git commit -m "Nueva versión"
   git push origin main
   ```

2. **GitHub Actions**:
   - Ejecuta tests (`test.yml`)
   - Crea release (`notify.yml`)
   - Notifica actualización disponible

3. **Actualización Automática**:
   - **PC**: `auto_updater.py` (cada hora)
   - **Android**: `ame_updater.py` (cada 6 horas)

---

## 📊 **Estado del Sistema**

| Componente          | Estado       | Descripción                          |
|---------------------|--------------|--------------------------------------|
| EventBus Local      | ✅ Conectado | ws://localhost:8765                 |
| Godot Bridge        | ✅ Conectado | ws://localhost:9090                 |
| Cloudflare Tunnel   | ✅ Activo    | https://random.trycloudflare.com   |
| AME Config          | ✅ Válido    | /sdcard/ame_config.json             |
| Versión             | 1.0.0        | Última versión                       |

---

## 📢 **Contribuir**

1. Haz un fork del repositorio
2. Crea una rama para tu feature: `git checkout -b feature/nueva-funcionalidad`
3. Haz commit de tus cambios: `git commit -m "Añadir nueva funcionalidad"`
4. Sube a la rama: `git push origin feature/nueva-funcionalidad`
5. Abre un Pull Request

---

## 📜 **Licencia**

MIT License

Copyright (c) 2026 AURA/AME Team

---