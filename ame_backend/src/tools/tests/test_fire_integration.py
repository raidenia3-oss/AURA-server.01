"""
Pruebas de Fuego — Sistemas Integrados de AURA.

Ejecuta dos tests internos de forma 100% autónoma y offline (sin llamadas de
red ni claves de IA reales):

  1. agents_pool.py: simula una consulta [COMPLEJA] y verifica que AURA-Architect
     y AURA-Shadow generen sus 2 rondas de debate y plasmen la síntesis.
  2. knowledge_ingest.py: inyecta un fragmento de código técnico y verifica que
     el boost de +0.15 del RAG semántico se aplique a recuerdos [KNOWLEDGE].

Salida tipo reporte (markdown) con PASS/FAIL por test.

Uso:
    python ame_backend/src/tools/tests/test_fire_integration.py
"""

from __future__ import annotations

import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

FAILS = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)


# --------------------------------------------------------------------------- #
# Mocks de motores (dict-shaped, imitan la respuesta real de ai_engine/router)
# --------------------------------------------------------------------------- #
class FakeAI:
    def __init__(self) -> None:
        self.calls: list = []

    def chat_with_tools(self, prompt: str = "") -> dict:
        self.calls.append(prompt)
        return {"text": f"[Architect][tools] solución limpia para: {prompt[:60]}"}

    def chat(self, prompt: str = "", context: str = "") -> dict:
        self.calls.append(prompt)
        return {"text": f"[AURA][synth] solución auditada y filtrada."}


class FakeRouter:
    def __init__(self) -> None:
        self.calls: list = []

    def chat(self, prompt: str = "", free_mode: bool = False) -> dict:
        self.calls.append((prompt, free_mode))
        return {"text": f"[Shadow][libre] abordaje crudo para: {prompt[:60]}"}


# --------------------------------------------------------------------------- #
# TEST 1 — agents_pool.py (debate [COMPLEJA])
# --------------------------------------------------------------------------- #
def test_agents_pool_debate() -> None:
    print("\n=== TEST 1: agents_pool.py — Debate [COMPLEJA] (Architect + Shadow) ===")
    from ame_backend.src.tools import agents_pool as ap

    ai = FakeAI()
    router = FakeRouter()
    pool = ap.AgentsPool(ai, router)

    task = "[COMPLEJA] diseña un sistema de ingestión RAG soberano con cifrado"
    assert ap.is_complex(task), "is_complex debe detectar [COMPLEJA]"

    result = pool.debate_sync(task)

    check("debate.ok", result.get("ok") is True)
    check("is_complex detectó [COMPLEJA]", ap.is_complex(task))
    # 2 rondas de Architect (chat_with_tools) + 1 síntesis (chat) = 3 llamadas.
    check(
        "Architect generó 2 rondas",
        len(ai.calls) == 3,
        f"llamadas Architect={len(ai.calls)} (esperado 3: 2 rondas + síntesis)",
    )
    # 2 rondas de Shadow (router.chat free_mode).
    check(
        "Shadow generó 2 rondas",
        len(router.calls) == 2 and all(fm for _, fm in router.calls),
        f"llamadas Shadow={len(router.calls)} free_mode=True",
    )
    check(
        "rondas == 2",
        result.get("rounds") == 2,
        f"rounds={result.get('rounds')}",
    )
    check(
        "síntesis presente en solution",
        bool(result.get("solution")),
        (result.get("solution") or "")[:50],
    )
    check(
        "Architect y Shadow en el payload",
        bool(result.get("architect")) and bool(result.get("shadow")),
    )


# --------------------------------------------------------------------------- #
# TEST 2 — knowledge_ingest.py + boost RAG +0.15
# --------------------------------------------------------------------------- #
def test_knowledge_ingest_boost() -> None:
    print("\n=== TEST 2: knowledge_ingest.py — Ingesta técnica + boost RAG +0.15 ===")

    # Stub de models para no tocar la BD real.
    import types

    models_stub = types.ModuleType("ame_backend.src.models")
    _store: list = []

    def save_memory(content, vector=None, kind="chat"):
        row = {"id": len(_store) + 1, "content": content, "vector": vector, "kind": kind}
        _store.append(row)
        return types.SimpleNamespace(**row)

    def memory_rows():
        return _store

    models_stub.save_memory = save_memory
    models_stub.memory_rows = memory_rows
    models_stub.recent_memories = lambda top_k: _store[-top_k:]

    import ame_backend.src as src_pkg
    import ame_backend.src.tools.knowledge_ingest as ki
    import ame_backend.src.neural_core as nc

    # Inyectar el stub en neural_core y knowledge_ingest.
    src_pkg.models = models_stub
    nc.models = models_stub
    ki.models = models_stub

    # Embeddings deterministas (no reales) para poder medir el boost de coseno.
    class FakeEmbedder:
        def __init__(self) -> None:
            self.enabled = True

        def embed(self, text: str):
            h = hash(text) & 0xFFFFFFFF
            base = [((h >> (8 * i)) & 0xFF) / 255.0 for i in range(8)]
            norm = sum(x * x for x in base) ** 0.5 or 1.0
            return [x / norm for x in base]

    nc.GeminiEmbedder = FakeEmbedder
    ki.SemanticMemory = nc.SemanticMemory  # reusa la clase con el embedder stub

    code_fragment = (
        "def fastapi_rag_query(app: FastAPI, q: str):\n"
        "    # Búsqueda semántica sobre la memoria de AURA\n"
        "    hits = semantic_memory.recall(q, top_k=5, technical=True)\n"
        "    return hits\n"
    )

    res = ki.ingest_text(code_fragment, source="fire-test")
    check("ingest.ok", res.get("ok") is True, f"chunks={res.get('chunks')}")
    check(
        "almacenó fragmentos [KNOWLEDGE]",
        res.get("stored", 0) > 0,
        f"stored={res.get('stored')}",
    )

    # Verificar el boost de +0.15 en recall() para consultas técnicas.
    mem = nc.SemanticMemory()
    # Ambos recuerdos comparten un vector "near" cuya similitud bruta con la
    # query es ~0.5 (bien por debajo de 0.85) para que el boost de +0.15 NO se
    # recorte a 1.0 y sea medible de forma exacta.
    q_emb = FakeEmbedder().embed("consulta tecnica de prueba")
    near = list(q_emb)
    near[0] = max(0.0, near[0] - 0.45)
    near[1] = max(0.0, near[1] - 0.45)
    norm = sum(x * x for x in near) ** 0.5 or 1.0
    near = [x / norm for x in near]
    _store.clear()
    _store.append(
        {"id": 1, "content": "[KNOWLEDGE] (fire-test) fragmento técnico",
         "vector": list(near), "kind": "[KNOWLEDGE]"}
    )
    _store.append(
        {"id": 2, "content": "chat normal sin etiqueta",
         "vector": list(near), "kind": "chat"}
    )

    hits = mem.recall("consulta tecnica de prueba", top_k=3, technical=True)
    check("recall devolvió resultados", len(hits) >= 1)

    knowledge_hit = next((h for h in hits if "[KNOWLEDGE]" in str(h.get("kind"))), None)
    normal_hit = next((h for h in hits if h.get("kind") == "chat"), None)

    if knowledge_hit and normal_hit:
        sim_k = knowledge_hit["similarity"]

        # Similitud bruta esperada (misma fórmula de coseno del RAG nativo).
        def _cos(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            na = sum(x * x for x in a) ** 0.5
            nb = sum(x * x for x in b) ** 0.5
            return dot / (na * nb) if na and nb else 0.0

        # La memoria [KNOWLEDGE] comparte el vector `near`; su similitud bruta
        # con la query es _cos(q_emb, near). El boost de +0.15 se suma encima.
        raw_k = round(_cos(list(q_emb), list(near)), 4)
        delta = round(sim_k - raw_k, 4)
        check(
            "boost +0.15 aplicado a [KNOWLEDGE]",
            abs(delta - 0.15) < 1e-6,
            f"delta={delta} (esperado 0.15)",
        )
        check(
            "recuerdo [KNOWLEDGE] priorizado",
            sim_k > raw_k,
            f"knowledge={sim_k} bruto={raw_k}",
        )
    else:
        check("boost +0.15 aplicado a [KNOWLEDGE]", False, "no se encontraron ambos hits")


def main() -> int:
    print("=" * 70)
    print("PRUEBAS DE FUEGO — Sistemas Integrados AURA")
    print("=" * 70)

    test_agents_pool_debate()
    test_knowledge_ingest_boost()

    print("\n" + "=" * 70)
    if FAILS:
        print(f"RESULTADO: {len(FAILS)} FALLO(S) -> {', '.join(FAILS)}")
        print("=" * 70)
        return 1
    print("RESULTADO: TODOS LOS TESTS PASS (0 FAIL)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
