// ═══════════════════════════════════════════════════════════════
// extension.js — Punto de entrada de la extensión VS Code
// Registra panel webview, comandos de teclado y handlers
// ═══════════════════════════════════════════════════════════════

const vscode = require("vscode");
const { CommandHandler } = require("./CommandHandler");
const { ColabClient } = require("./ColabClient");

/** Activar extensión */
function activate(context) {
    console.log("AME Agent VS Code activado");

    // Inicializar cliente Colab
    const colab = new ColabClient();
    const handler = new CommandHandler(colab);

    // Panel lateral webview
    const provider = new AMEAgentPanel(colab, handler);

    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider("ameAgentPanel", provider),
    );

    // Comando: abrir panel
    context.subscriptions.push(
        vscode.commands.registerCommand("ameAgent.openPanel", () => {
            vscode.commands.executeCommand("workbench.view.extension.ame-agent");
        }),
    );

    // Comando: enviar selección al agente
    context.subscriptions.push(
        vscode.commands.registerCommand("ameAgent.sendSelection", () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            const sel = editor.document.getText(editor.selection);
            if (sel) provider.postMessage({ type: "input", text: sel });
        }),
    );
}

/** WebViewProvider del panel lateral */
class AMEAgentPanel {
    constructor(colab, handler) {
        this.colab = colab;
        this.handler = handler;
        this._view = null;
    }

    resolveWebviewView(webviewView) {
        this._view = webviewView;
        webviewView.webview.options = { enableScripts: true };
        webviewView.webview.html = getHtml();

        // Escuchar mensajes desde el webview
        webviewView.webview.onDidReceiveMessage(async (msg) => {
            if (msg.type === "chat") {
                webviewView.webview.postMessage({ type: "status", text: "Pensando..." });
                try {
                    const response = await this.colab.send(msg.text);
                    webviewView.webview.postMessage({ type: "response", text: response });
                } catch {
                    webviewView.webview.postMessage({
                        type: "error",
                        text: "Servidor Colab no disponible",
                    });
                }
            }

            if (msg.type === "action" && msg.action) {
                const result = await this.handler.execute(msg.action, msg.args);
                webviewView.webview.postMessage({ type: "actionResult", result });
            }
        });
    }

    postMessage(msg) {
        this._view?.webview.postMessage(msg);
    }
}

/** HTML del panel webview */
function getHtml() {
    return `<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui,-apple-system,sans-serif}
body{background:#0d1117;color:#c9d1d9;height:100vh;display:flex;flex-direction:column}
.header{background:#161b22;padding:10px 14px;border-bottom:1px solid #30363d}
.header h1{font-size:14px;color:#58a6ff;font-weight:600}
.header .sub{font-size:10px;color:#8b949e;margin-top:2px}
.messages{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px}
.msg{max-width:92%;padding:9px 12px;border-radius:8px;font-size:12px;line-height:1.5}
.msg.user{background:#1f6feb20;border:0.5px solid #1f6feb30;align-self:flex-end}
.msg.assistant{background:#21262d;border:0.5px solid #30363d;align-self:flex-start}
.msg .badge{font-size:9px;color:#8b949e;margin-top:4px}
.msg .actions{display:flex;gap:6px;margin-top:6px}
.msg .actions button{font-size:9px;padding:2px 8px;border-radius:4px;cursor:pointer;background:#21262d;color:#58a6ff;border:0.5px solid #30363d}
.input-bar{display:flex;gap:8px;padding:10px 12px;border-top:1px solid #30363d;background:#161b22}
.input-bar input{flex:1;background:#21262d;border:0.5px solid #30363d;border-radius:6px;padding:8px 12px;font-size:12px;color:#c9d1d9;outline:none}
.input-bar button{background:#238636;color:#fff;border:none;border-radius:6px;padding:8px 14px;font-size:12px;cursor:pointer}
.status-bar{display:flex;gap:8px;padding:6px 12px;font-size:9px;color:#8b949e;border-top:1px solid #30363d;background:#161b22}
.status-dot{width:6px;height:6px;border-radius:50%;display:inline-block}
.dot-active{background:#3fb950}
.dot-inactive{background:#ff7b72}
</style></head>
<body>
<div class="header"><h1>AME Agent</h1><div class="sub">IA local sin censura · Colab</div></div>
<div class="messages" id="messages"></div>
<div class="input-bar">
  <input id="input" placeholder="Pregunta al agente..." onkeydown="if(event.key==='Enter')send()"/>
  <button onclick="send()">➤</button>
</div>
<div class="status-bar" id="statusBar">
  <span class="status-dot" id="statusDot"></span>
  <span id="statusText">Conectando...</span>
</div>
<script>
const vscode = acquireVsCodeApi();
const msgs = document.getElementById('messages');
const input = document.getElementById('input');

function addMsg(text, role) {
  const d = document.createElement('div');
  d.className = 'msg ' + role;
  d.textContent = text;
  msgs.appendChild(d);
  msgs.scrollTop = msgs.scrollHeight;
}

function send() {
  const t = input.value.trim();
  if (!t) return;
  addMsg(t, 'user');
  input.value = '';
  vscode.postMessage({ type: 'chat', text: t });
}

window.addEventListener('message', e => {
  const msg = e.data;
  if (msg.type === 'response') addMsg(msg.text, 'assistant');
  if (msg.type === 'error') addMsg('❌ ' + msg.text, 'assistant');
  if (msg.type === 'status') document.getElementById('statusText').textContent = msg.text;
});

document.getElementById('statusDot').className = 'status-dot dot-active';
document.getElementById('statusText').textContent = 'Listo';
</script>
</body></html>`;
}

exports.activate = activate;
