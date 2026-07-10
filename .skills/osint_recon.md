# Skill: OSINT Reconnaissance (Expert Level)

## 🎯 Objetivo
Ejecutar el ciclo de inteligencia de fuentes abiertas (OSINT) para identificar huellas digitales, activos expuestos y metadatos, priorizando el sigilo y la eficiencia de recursos.

## 🛠️ Protocolos de Ejecución

### 1. Búsqueda de Usernames (Multi-Platform)
Cuando el usuario proporcione un `@username` o `nombre_usuario`:
- **Técnica**: Búsqueda cruzada en redes sociales y foros.
- **Acción**: Verificar disponibilidad/existencia en plataformas clave (GitHub, Twitter, LinkedIn, Instagram).
- **Comando AME**: `python AME/recon.py --user [username]`

### 2. Análisis de Metadatos Locales
Cuando se detecte una imagen o archivo multimedia:
- **Técnica**: Extracción de EXIF y metadatos forenses.
- **Acción**: Buscar coordenadas GPS, fecha de captura y modelo de dispositivo.
- **Comando AME**: `python AME/recon.py --meta [ruta_archivo]`

### 3. Google Dorking Seguro
Para búsquedas de activos expuestos:
- **Operadores Críticos**:
    - `intitle:"index of" "parent directory"` $\rightarrow$ Para encontrar directorios abiertos.
    - `filetype:sql` o `filetype:env` $\rightarrow$ Para buscar bases de datos o archivos de configuración expuestos.
    - `site:target.com "confidential"` $\rightarrow$ Para filtrar información sensible en un dominio.
- **Regla de Seguridad**: No realizar más de 3 búsquedas complejas por minuto para evitar captchas y bloqueos de IP.

## ⚙️ Integración con AME
El agente debe utilizar los siguientes alias para ejecutar herramientas en el celular:
- `recon --user` $\rightarrow$ Búsqueda de identidad digital.
- `recon --meta` $\rightarrow$ Forense de archivos.
- `recon --whois` $\rightarrow$ Análisis de dominio.

## 📄 Formato de Salida
Todo resultado debe ser sintetizado en un JSON compacto:
`{"target": "...", "findings": [], "risk_level": "low|med|high"}`