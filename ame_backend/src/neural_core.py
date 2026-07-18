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
    """Perceptrón simple multi-entrada -> una salida (estabilidad 0..1)."""

    # Entradas esperadas en orden fijo:
    #   0: latency_norm   (latencia normalizada 0..1, 1 = malo)
    #   1: mem_norm       (uso de memoria normalizado 0..1)
    #   2: health_pings   (pings de salud recientes 0..1)
    #   3: msg_rate       (tasa de mensajes 0..1)
    N_INPUTS = 4

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
        """Normaliza Sys Vitals a las 4 entradas del perceptrón."""
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

        return [latency_norm, mem_norm, health_norm, msg_norm]

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
        # Semilla inicial razonable: penalizar latencia/memoria altas.
        return cls(weights=[0.2, 0.1, -0.5, -0.3], bias=0.0, learning_rate=0.05, iterations=0)


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
