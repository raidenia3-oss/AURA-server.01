/**
 * AURA Hologram Gestures — MediaPipe Hands Integration
 * Captura gestos de la mano para interacción táctil sin contacto.
 * Usa el dedo índice como cursor 3D.
 */

let hands = null;
let camera = null;
let gestureCanvas = null;
let gestureCtx = null;
let gestureVideo = null;
let gestureStatusEl = null;
let isRunning = false;
let lastIndexX = 0, lastIndexY = 0;

// Inicializar MediaPipe Hands
async function initHologramGestures() {
    gestureCanvas = document.getElementById('gestureCanvas');
    gestureVideo = document.getElementById('gestureVideo');
    gestureStatusEl = document.getElementById('gestureStatus');

    if (!gestureCanvas || !gestureVideo || !gestureStatusEl) {
        console.warn('Hologram gestures: missing elements');
        return;
    }

    gestureCtx = gestureCanvas.getContext('2d');
    gestureCanvas.width = gestureCanvas.offsetWidth;
    gestureCanvas.height = gestureCanvas.offsetHeight;

    try {
        // Cargar MediaPipe Hands
        const handsModule = await import('https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1646424915/hands.min.js');
        const cameraUtils = await import('https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils@0.4.1646424915/camera_utils.min.js');

        hands = new handsModule.Hands({
            locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1646424915/${file}`
        });

        hands.setOptions({
            maxNumHands: 1,
            modelComplexity: 1,
            minDetectionConfidence: 0.7,
            minTrackingConfidence: 0.7
        });

        hands.onResults(onHandsResults);

        // Iniciar cámara
        camera = new cameraUtils.Camera(gestureVideo, {
            onFrame: async () => {
                if (isRunning) {
                    await hands.send({ image: gestureVideo });
                }
            },
            width: gestureCanvas.width,
            height: gestureCanvas.height
        });

        gestureStatusEl.textContent = '📹 Webcam: ON';
        gestureStatusEl.style.color = 'var(--green)';
        isRunning = true;
        console.log('Hologram gestures: initialized');

    } catch (e) {
        gestureStatusEl.textContent = '📹 Webcam: ERROR';
        gestureStatusEl.style.color = 'var(--red)';
        console.error('Hologram gestures init error:', e);
    }
}

// Procesar resultados de MediaPipe
function onHandsResults(results) {
    if (!gestureCtx || !gestureCanvas) return;

    // Limpiar canvas
    gestureCtx.clearRect(0, 0, gestureCanvas.width, gestureCanvas.height);

    // Dibujar video
    gestureCtx.save();
    gestureCtx.scale(-1, 1);
    gestureCtx.translate(-gestureCanvas.width, 0);
    gestureCtx.drawImage(results.image, 0, 0, gestureCanvas.width, gestureCanvas.height);
    gestureCtx.restore();

    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
        const landmarks = results.multiHandLandmarks[0];

        // Dibujar puntos de la mano
        for (let i = 0; i < landmarks.length; i++) {
            const x = landmarks[i].x * gestureCanvas.width;
            const y = landmarks[i].y * gestureCanvas.height;

            // Dedo índice (punto 8)
            if (i === 8) {
                lastIndexX = x;
                lastIndexY = y;
                gestureCtx.fillStyle = 'rgba(0, 212, 255, 0.8)';
                gestureCtx.beginPath();
                gestureCtx.arc(x, y, 8, 0, 2 * Math.PI);
                gestureCtx.fill();
                gestureCtx.strokeStyle = 'rgba(0, 212, 255, 1)';
                gestureCtx.lineWidth = 2;
                gestureCtx.stroke();
            } else {
                // Otros puntos
                gestureCtx.fillStyle = 'rgba(124, 92, 252, 0.6)';
                gestureCtx.beginPath();
                gestureCtx.arc(x, y, 4, 0, 2 * Math.PI);
                gestureCtx.fill();
            }
        }

        // Dibujar conexiones
        gestureCtx.strokeStyle = 'rgba(124, 92, 252, 0.4)';
        gestureCtx.lineWidth = 1;
        for (const connection of handsModule.HAND_CONNECTIONS) {
            const start = connection[0];
            const end = connection[1];
            gestureCtx.beginPath();
            gestureCtx.moveTo(landmarks[start].x * gestureCanvas.width, landmarks[start].y * gestureCanvas.height);
            gestureCtx.lineTo(landmarks[end].x * gestureCanvas.width, landmarks[end].y * gestureCanvas.height);
            gestureCtx.stroke();
        }

        // Mostrar coordenadas del índice
        const coordText = `📍 ${Math.round(lastIndexX)}, ${Math.round(lastIndexY)}`;
        gestureCtx.fillStyle = 'rgba(0, 212, 255, 0.9)';
        gestureCtx.font = '0.7rem JetBrains Mono';
        gestureCtx.fillText(coordText, 10, 20);
    }
}

// Detener gestos
function stopHologramGestures() {
    if (camera) {
        camera.stop();
        camera = null;
    }
    if (hands) {
        hands.close();
        hands = null;
    }
    isRunning = false;
    if (gestureStatusEl) {
        gestureStatusEl.textContent = '📹 Webcam: OFF';
        gestureStatusEl.style.color = 'var(--text-dim)';
    }
}

// Exportar API global
window.hologramGestures = {
    init: initHologramGestures,
    stop: stopHologramGestures,
    getIndexPosition: () => ({ x: lastIndexX, y: lastIndexY })
};

// Inicializar al cargar
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    initHologramGestures();
} else {
    document.addEventListener('DOMContentLoaded', initHologramGestures);
}