"""
Núcleo Evolutivo — La Neurona Artificial Nativa de AURA.

``AuraPerceptron`` es un perceptrón entrenado desde cero con matemáticas
puras de Python (sin librerías pesadas). Sus entradas son las métricas de
Sys Vitals (latencia, uso de memoria, pings de salud) y aprende a predecir
la "Estabilidad del Sistema" (0..1). Cuando la estabilidad cae por debajo
de un umbral (servidor entrando en inactividad / riesgo de dormirse),
dispara una señal de keep-alive para mantener el sistema en línea.

El estado (pesos, bias, learning_rate, iteraciones) se persiste en la tabla
``neural_state`` en cada iteración, de modo que la neurona conserva lo
aprendido aunque el servidor se reinicie.
"""

from __future__ import annotations

import json
import math
import os
import random
from typing import List, Optional

try:
    from ame_backend.src import models
except Exception:  # pragma: no cover - import relativo en pruebas
    import models  # type: ignore

try:
    from ame_backend.src import neural_telemetry
except Exception:  # pragma: no cover
    neural_telemetry = None  # type: ignore


def _sigmoid(x: float) -> float:
    """Función de activación logística, estable ante overflow."""
    if x <= -45.0:
        return 0.0
    if x >= 45.0:
        return 1.0
    return 1.0 / (1.0 + math.exp(-x))


def _leaky_relu(x: float, alpha: float = 0.01) -> float:
    return x if x >= 0 else alpha * x


class AuraPerceptron:
    """Perceptrón simple multi-entrada -> una salida (estabilidad 0..1).

    Evolución Neural (Fase Enjambre): de 4 a 8 entradas. Además de las
    métricas de Sys Vitals, ahora absorbe señales de las nuevas herramientas
    de AURA para ser más predictiva:
      - 4 entradas base (latencia, memoria, pings, tasa de mensajes)
      - rag_hit_rate:        tasa de acierto del RAG semántico (0..1)
      - router_err_rate:     tasa de error del enrutador multi-modelo (0..1)
      - workspace_block_rate: intentos de path traversal bloqueados (0..1)
      - tool_activity:       actividad de operación de AURA (0..1)
    """

    # Entradas esperadas en orden fijo:
    #   0: latency_norm   (latencia normalizada 0..1, 1 = malo)
    #   1: mem_norm       (uso de memoria normalizado 0..1)
    #   2: health_norm    (riesgo por falta de pings 0..1)
    #   3: msg_rate       (tasa de mensajes 0..1)
    #   4: rag_hit_rate   (acierto RAG semántico 0..1)
    #   5: router_err_rate(error del enrutador 0..1)
    #   6: workspace_block_rate (traversal bloqueado 0..1)
    #   7: tool_activity  (operación de AURA 0..1)
    N_INPUTS = 8

    # Si la estabilidad predicha cae bajo esto, el sistema se considera
    # en riesgo de inactividad -> debe forzar actividad (keep-alive).
    INSTABILITY_THRESHOLD = 0.35

    def __init__(
        self,
        weights: Optional[List[float]] = None,
        bias: float = 0.0,
        learning_rate: float = 0.05,
        iterations: int = 0,
    ) -> None:
        if weights is not None and len(weights) == self.N_INPUTS:
            self.weights = list(weights)
        else:
            # Semilla determinista pero distinta por arranque si no hay estado.
            random.seed(os.getpid() + iterations)
            self.weights = [random.uniform(-0.5, 0.5) for _ in range(self.N_INPUTS)]
        self.bias = float(bias)
        self.learning_rate = float(learning_rate)
        self.iterations = int(iterations)

    # ------------------------------------------------------------------ #
    # Propagación (forward)
    # ------------------------------------------------------------------ #
    def predict(self, inputs: List[float]) -> float:
        """Devuelve la estabilidad predicha en 0..1."""
        if len(inputs) != self.N_INPUTS:
            raise ValueError(f"Se esperan {self.N_INPUTS} entradas, recibí {len(inputs)}")
        z = self.bias
        for w, x in zip(self.weights, inputs):
            z += w * x
        return _sigmoid(z)

    def stability_from_vitals(self, vitals: dict) -> float:
        """Convierte Sys Vitals crudos a estabilidad 0..1."""
        inputs = self.vitals_to_inputs(vitals)
        return self.predict(inputs)

    @staticmethod
    def vitals_to_inputs(v: dict) -> List[float]:
        """Normaliza Sys Vitals + telemetría de herramientas a 8 entradas."""
        latency = float(v.get("latency_ms", 0.0))
        # Latencia: <=50ms -> 0 (bueno), >=2000ms -> 1 (malo).
        latency_norm = min(1.0, max(0.0, latency / 2000.0))

        mem = float(v.get("memory_percent", 0.0))
        mem_norm = min(1.0, max(0.0, mem / 100.0))

        health_pings = float(v.get("health_pings", 1.0))
        # 0 pings -> 1 (riesgo); >=3 pings -> 0 (sano).
        health_norm = min(1.0, max(0.0, 1.0 - health_pings / 3.0))

        msg_rate = float(v.get("msg_rate", 0.0))
        msg_norm = min(1.0, max(0.0, msg_rate))

        # Nuevas entradas de las herramientas (0..1).
        rag_hit_rate = min(1.0, max(0.0, float(v.get("rag_hit_rate", 0.0))))
        router_err_rate = min(1.0, max(0.0, float(v.get("router_err_rate", 0.0))))
        workspace_block_rate = min(1.0, max(0.0, float(v.get("workspace_block_rate", 0.0))))
        tool_activity = min(1.0, max(0.0, float(v.get("tool_activity", 0.0))))

        return [
            latency_norm,
            mem_norm,
            health_norm,
            msg_norm,
            rag_hit_rate,
            router_err_rate,
            workspace_block_rate,
            tool_activity,
        ]

    # ------------------------------------------------------------------ #
    # Aprendizaje (backprop de un solo paso / regla delta)
    # ------------------------------------------------------------------ #
    def train_step(self, inputs: List[float], target: float) -> float:
        """Un paso de entrenamiento supervisado. Retorna el error abs."""
        if len(inputs) != self.N_INPUTS:
            raise ValueError(f"Se esperan {self.N_INPUTS} entradas, recibí {len(inputs)}")

        z = self.bias
        for w, x in zip(self.weights, inputs):
            z += w * x
        y = _sigmoid(z)
        error = target - y
        # Gradiente de la sigmoide: y * (1 - y)
        d = y * (1.0 - y)
        grad = error * d

        for i in range(self.N_INPUTS):
            self.weights[i] += self.learning_rate * grad * inputs[i]
        self.bias += self.learning_rate * grad

        self.iterations += 1
        return abs(error)

    def compute_target(self, vitals: dict, alive: bool) -> float:
        """Etiqueta de estabilidad real para entrenar.

        Si el sistema está vivo y sano, la estabilidad objetivo es alta.
        Si hay inactividad real (sin pings de salud Y sin mensajes), la
        estabilidad cae por debajo del umbral para forzar keep-alive.
        """
        score = 1.0
        pings = float(vitals.get("health_pings", 1.0))
        msgs = float(vitals.get("msg_rate", 0.0))
        latency = float(vitals.get("latency_ms", 0.0))
        if pings <= 0 and msgs <= 0:
            # Inactividad total -> riesgo de dormirse en plan free.
            score -= 0.75
        else:
            if pings <= 0:
                score -= 0.35
            if msgs <= 0:
                score -= 0.2
        if latency >= 1500:
            score -= 0.2
        # Nuevas señales de herramientas (Fase Enjambre).
        router_err_rate = float(vitals.get("router_err_rate", 0.0))
        if router_err_rate >= 0.5:
            score -= 0.2  # enrutador multi-modelo fallando seguido
        tool_activity = float(vitals.get("tool_activity", 0.0))
        if tool_activity > 0:
            score += 0.1  # sistema operando activamente = más estable
        if not alive:
            score -= 0.3
        return min(1.0, max(0.0, score))

    # ------------------------------------------------------------------ #
    # Persistencia
    # ------------------------------------------------------------------ #
    def save(self, last_stability: Optional[float] = None) -> None:
        try:
            models.save_neural_state(
                weights=self.weights,
                bias=self.bias,
                learning_rate=self.learning_rate,
                iterations=self.iterations,
                last_stability=last_stability,
            )
        except Exception as exc:  # pragma: no cover - resiliencia
            print(f"[NeuralCore] No se pudo persistir el estado: {exc}")

    @classmethod
    def load_or_init(cls) -> "AuraPerceptron":
        try:
            state = models.load_neural_state()
        except Exception as exc:  # pragma: no cover
            print(f"[NeuralCore] No se pudo cargar el estado: {exc}")
            state = None
        if state:
            return cls(
                weights=state["weights"],
                bias=state["bias"],
                learning_rate=state["learning_rate"],
                iterations=state["iterations"],
            )
        # Semilla inicial razonable (8 entradas):
        # penalizar latencia/memoria/router-err, reforzar pings/rag/tools.
        return cls(
            weights=[0.2, 0.1, -0.5, -0.3, 0.1, 0.2, 0.05, -0.2],
            bias=0.0,
            learning_rate=0.05,
            iterations=0,
        )


class EvolutionCore:
    """Orquesta la neurona + Sys Vitals + keep-alive.

    Cada tick:
      1. Toma métricas reales (Sys Vitals).
      2. Predice estabilidad con la neurona.
      3. Si está por debajo del umbral -> dispara keep-alive (callback).
      4. Entrena un paso con el objetivo real y persiste.
    """

    def __init__(self, keep_alive_fn=None) -> None:
        self.brain = AuraPerceptron.load_or_init()
        self.keep_alive_fn = keep_alive_fn
        self.keep_alive_fired = 0
        self.last_stability: Optional[float] = None
        self.last_error: Optional[float] = None

    def tick(self, vitals: dict, alive: bool = True) -> dict:
        # Inyectar telemetría de herramientas como nuevas entradas (Fase Enjambre).
        if neural_telemetry is not None:
            try:
                vitals = {**vitals, **neural_telemetry.snapshot()}
            except Exception:
                pass
        inputs = self.brain.vitals_to_inputs(vitals)
        stability = self.brain.predict(inputs)
        self.last_stability = stability

        # Inactividad real (ground truth): sin pings de salud Y sin mensajes.
        # En el plan free de Render esto significa que la instancia se dormirá.
        health_pings = float(vitals.get("health_pings", 1.0))
        msg_rate = float(vitals.get("msg_rate", 0.0))
        real_inactivity = (health_pings <= 0) and (msg_rate <= 0)

        instability = (stability < self.brain.INSTABILITY_THRESHOLD) or real_inactivity
        if instability and self.keep_alive_fn is not None:
            try:
                self.keep_alive_fn()
                self.keep_alive_fired += 1
            except Exception as exc:  # pragma: no cover
                print(f"[EvolutionCore] keep-alive falló: {exc}")

        target = self.brain.compute_target(vitals, alive and not instability)
        err = self.brain.train_step(inputs, target)
        self.last_error = err

        # Persistir el aprendizaje adquirido en cada iteración.
        self.brain.save(last_stability=stability)

        return {
            "stability": stability,
            "instability": instability,
            "real_inactivity": real_inactivity,
            "weights": list(self.brain.weights),
            "bias": self.brain.bias,
            "learning_rate": self.brain.learning_rate,
            "iterations": self.brain.iterations,
            "keep_alive_fired": self.keep_alive_fired,
            "train_error": err,
        }

    def status(self) -> dict:
        return {
            "weights": list(self.brain.weights),
            "bias": self.brain.bias,
            "learning_rate": self.brain.learning_rate,
            "iterations": self.brain.iterations,
            "last_stability": self.last_stability,
            "last_error": self.last_error,
            "keep_alive_fired": self.keep_alive_fired,
            "threshold": self.brain.INSTABILITY_THRESHOLD,
        }


# --------------------------------------------------------------------------- #
# Memoria Semántica (RAG) — embeddings de Gemini + coseno nativo
# --------------------------------------------------------------------------- #
def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Similitud de coseno con matemáticas puras de Python."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    denom = math.sqrt(na) * math.sqrt(nb)
    if denom == 0.0:
        return 0.0
    return dot / denom


class GeminiEmbedder:
    """Genera embeddings usando la API de Gemini (embedding-001)."""

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_EMBED_MODEL", "embedding-001")
        self.base_url = os.getenv(
            "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
        )
        self.enabled = bool(self.api_key)

    def embed(self, text: str) -> Optional[List[float]]:
        """Devuelve el vector de embedding o None si no hay API key."""
        if not self.enabled or not text:
            return None
        url = (
            f"{self.base_url}/models/{self.model}:batchEmbedContents"
            f"?key={self.api_key}"
        )
        payload = {
            "requests": [
                {"model": f"models/{self.model}", "content": {"parts": [{"text": text}]}}
            ]
        }
        try:
            import requests  # stdlib-friendly, ya en requirements

            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            # Respuesta: { "embeddings": [ { "values": [...] } ] }
            emb = data.get("embeddings", [{}])[0]
            return emb.get("values")
        except Exception as exc:  # pragma: no cover - resiliencia
            print(f"[GeminiEmbedder] fallo: {exc}")
            return None


class SemanticMemory:
    """RAG nativo: guarda recuerdos + embeddings y recupera los
    más parecidos al contexto actual por coseno.
    """

    def __init__(self) -> None:
        self.embedder = GeminiEmbedder()

    def remember(
        self, content: str, kind: str = "chat"
    ) -> Optional[int]:
        """Genera embedding y persiste el recuerdo en ``semantic_memory``."""
        vector = self.embedder.embed(content)
        try:
            row = models.save_memory(content=content, vector=vector, kind=kind)
            return row.id
        except Exception as exc:  # pragma: no cover
            print(f"[SemanticMemory] no se guardó: {exc}")
            return None

    def recall(self, query: str, top_k: int = 3, min_sim: float = 0.25) -> List[dict]:
        """Busca los ``top_k`` recuerdos más similares a ``query``."""
        q_vec = self.embedder.embed(query)
        if q_vec is None:
            # Sin embeddings: devolvemos los más recientes como fallback.
            return models.recent_memories(top_k)
        rows = models.memory_rows()
        scored = []
        for r in rows:
            if not r["vector"]:
                continue
            sim = cosine_similarity(q_vec, r["vector"])
            if sim >= min_sim:
                scored.append((sim, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "id": r["id"],
                "content": r["content"],
                "kind": r["kind"],
                "similarity": round(sim, 4),
            }
            for sim, r in scored[:top_k]
        ]

    def build_context(self, query: str, top_k: int = 3) -> str:
        """Arma un bloque de contexto RAG para inyectar en el prompt."""
        hits = self.recall(query, top_k=top_k)
        if not hits:
            return ""
        lines = ["[Memoria semántica de AURA — recuerdos relacionados]"]
        for h in hits:
            lines.append(f"- ({h['similarity']}) {h['content'][:400]}")
        return "\n".join(lines)

