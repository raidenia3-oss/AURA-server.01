"""
Pruebas del Sandbox de Ejecución Dinámica — AURA.

Valida dos escenarios críticos de forma 100% autónoma y offline:
  1. Caso de ÉXITO: ejecuta la serie de Fibonacci y comprueba que el stdout
     impreso coincide con el valor esperado.
  2. Caso de CONTROL DE DAÑOS: ejecuta un bucle infinito (while True: pass)
     y verifica que el Sandbox lo interrumpe limpiamente al superar el timeout
     SIN colgar el backend (el proceso hijo es terminado).

Uso:
    python ame_backend/src/tools/tests/test_sandbox.py
"""

from __future__ import annotations

import asyncio
import sys

FAILS = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)


async def _scenario_success() -> None:
    print("\n=== Caso de ÉXITO: Serie de Fibonacci ===")
    from ame_backend.src.tools import code_sandbox as cs

    # Fibonacci(15) = 610.
    code = (
        "def fib(n):\n"
        "    a, b = 0, 1\n"
        "    for _ in range(n):\n"
        "        a, b = b, a + b\n"
        "    return a\n"
        "print('FIB15:', fib(15))\n"
    )
    res = await cs.execute_code(code, timeout=5)
    check("ok=True", res.get("ok") is True, f"rc={res.get('returncode')}")
    check("sin timeout", res.get("timed_out") is False)
    check("stdout contiene FIB15: 610",
          "FIB15: 610" in (res.get("stdout") or ""),
          (res.get("stdout") or "").strip()[:60])


async def _scenario_infinite_loop() -> None:
    print("\n=== Caso de CONTROL DE DAÑOS: Bucle infinito ===")
    from ame_backend.src.tools import code_sandbox as cs

    code = "while True:\n    pass\n"
    # Timeout corto para que la prueba sea rápida.
    res = await cs.execute_code(code, timeout=2)
    check("marcado como timed_out", res.get("timed_out") is True)
    check("ok=False tras timeout", res.get("ok") is False)
    check("sin colgar: retornó dict", isinstance(res, dict))
    check("proceso hijo no vivo (rc!=None o timed_out)",
          res.get("timed_out") is True or res.get("returncode") is not None)


def main() -> int:
    print("=" * 64)
    print("PRUEBAS DEL SANDBOX DE EJECUCIÓN DINÁMICA — AURA")
    print("=" * 64)
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    asyncio.run(_scenario_success())
    asyncio.run(_scenario_infinite_loop())
    print("\n" + "=" * 64)
    if FAILS:
        print(f"RESULTADO: {len(FAILS)} FALLO(S) -> {', '.join(FAILS)}")
        print("=" * 64)
        return 1
    print("RESULTADO: TODOS LOS TESTS PASS (0 FAIL)")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
