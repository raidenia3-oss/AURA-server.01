// ═══════════════════════════════════════════════════════════════
// ColabClient.js — Cliente para servidores Colab (VS Code)
// Conexión a servidores de IA sin censura para la extensión
// ═══════════════════════════════════════════════════════════════

const https = require("https");
const http = require("http");

const CODE_SERVER = "https://scabbed-uneven-habitant.ngrok-free.dev";
const GENERAL_SERVER = "https://scabbed-uneven-habitant.ngrok-free.dev";

/** Palabras clave para detectar preguntas de código */
const CODE_KEYWORDS = [
    "código",
    "codigo",
    "script",
    "python",
    "javascript",
    "typescript",
    "java",
    "html",
    "css",
    "programar",
    "función",
    "funcion",
    "bucle",
    "npm",
    "pip",
    "install",
    "debug",
    "depurar",
    "error",
];

class ColabClient {
    constructor() {
        this.codeUrl = CODE_SERVER;
        this.generalUrl = GENERAL_SERVER;
    }

    /** Enviar mensaje al servidor Colab adecuado */
    async send(message) {
        const type = this.detectType(message);
        const url = type === "code" ? this.codeUrl : this.generalUrl;

        try {
            const response = await this.fetchPost(url, {
                message,
                stream: false,
            });
            return response.response || response.choices?.[0]?.message?.content || "Sin respuesta";
        } catch (err) {
            // Failover: intentar el otro servidor
            const fallbackUrl = type === "code" ? this.generalUrl : this.codeUrl;
            try {
                const response = await this.fetchPost(fallbackUrl, { message, stream: false });
                return (
                    (response.response ||
                        response.choices?.[0]?.message?.content ||
                        "Sin respuesta") + "\n\n(respondido por servidor alternativo)"
                );
            } catch {
                throw new Error("Servidores Colab no disponibles");
            }
        }
    }

    /** Detectar tipo de pregunta */
    detectType(message) {
        const lower = message.toLowerCase();
        for (const kw of CODE_KEYWORDS) {
            if (lower.includes(kw)) return "code";
        }
        return "general";
    }

    /** POST a URL con JSON */
    fetchPost(url, body) {
        return new Promise((resolve, reject) => {
            const urlObj = new URL(url);
            const data = JSON.stringify(body);
            const lib = url.startsWith("https") ? https : http;

            const req = lib.request(
                {
                    hostname: urlObj.hostname,
                    port: urlObj.port || (url.startsWith("https") ? 443 : 80),
                    path: urlObj.pathname || "/",
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Content-Length": Buffer.byteLength(data),
                    },
                    timeout: 30000,
                },
                (res) => {
                    let chunks = "";
                    res.on("data", (chunk) => (chunks += chunk));
                    res.on("end", () => {
                        try {
                            resolve(JSON.parse(chunks));
                        } catch {
                            reject(new Error("Respuesta inválida del servidor"));
                        }
                    });
                },
            );

            req.on("error", reject);
            req.on("timeout", () => {
                req.destroy();
                reject(new Error("Timeout"));
            });
            req.write(data);
            req.end();
        });
    }

    /** Verificar estado del servidor */
    async healthCheck(url) {
        try {
            await this.fetchPost(url || this.codeUrl, { message: "ping", stream: false });
            return true;
        } catch {
            return false;
        }
    }
}

exports.ColabClient = ColabClient;
