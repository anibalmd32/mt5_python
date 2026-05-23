"""Explora el catálogo de símbolos disponibles en el terminal MT5.

Para un usuario sin experiencia: un "símbolo" es cada instrumento que el broker
ofrece para operar (EUR/USD, oro, Bitcoin, índice S&P 500, etc.). Cada broker
expone su propia lista; este script la lee, la agrupa por categoría y la
muestra de forma legible.
"""

from collections import defaultdict
from dataclasses import dataclass

import MetaTrader5 as mt5


@dataclass
class SymbolRow:
    category: str
    name: str
    spread_points: int
    digits: int
    visible: bool
    description: str


def _categorize(path: str) -> str:
    """Extrae la primera carpeta del `path` del símbolo.

    MT5 organiza los símbolos en un árbol tipo carpeta:
        'Forex\\Majors\\EURUSD'   -> 'Forex'
        'Crypto\\BTCUSD'          -> 'Crypto'
        'EURUSD' (sin árbol)      -> 'Otros'
    """
    if not path or "\\" not in path:
        return "Otros"
    return path.split("\\", 1)[0]


def _collect_symbols(filter_pattern: str | None) -> list[SymbolRow]:
    raw = mt5.symbols_get(filter_pattern) if filter_pattern else mt5.symbols_get()
    if raw is None:
        return []
    return [
        SymbolRow(
            category=_categorize(s.path),
            name=s.name,
            spread_points=s.spread,
            digits=s.digits,
            visible=s.visible,
            description=s.description or "",
        )
        for s in raw
    ]


def _print_summary(rows: list[SymbolRow]) -> None:
    by_cat: dict[str, int] = defaultdict(int)
    for r in rows:
        by_cat[r.category] += 1

    print(f"\nTotal de símbolos: {len(rows)}")
    print("\nPor categoría:")
    for cat in sorted(by_cat):
        print(f"  {cat:<20} {by_cat[cat]:>4} símbolos")


def _print_listing(rows: list[SymbolRow], limit: int) -> None:
    rows_sorted = sorted(rows, key=lambda r: (r.category, r.spread_points, r.name))
    shown = rows_sorted[:limit]

    print(f"\nListado ({len(shown)} de {len(rows)}, ordenado por categoría y spread):")
    print("-" * 78)
    print(f"{'Categoría':<14} {'Símbolo':<14} {'Spread (pts)':>12} {'Decimales':>10} {'Visible':>8}")
    print("-" * 78)
    for r in shown:
        visible = "sí" if r.visible else "no"
        print(f"{r.category:<14} {r.name:<14} {r.spread_points:>12} {r.digits:>10} {visible:>8}")


def run(filter_pattern: str | None = None, limit: int = 20) -> None:
    """Lista los símbolos del terminal, agrupados por categoría.

    Args:
        filter_pattern: patrón al estilo MT5 (`*USD*`, `EUR*`, `*,!*USD*`...).
            Si es None se devuelven todos.
        limit: cuántos símbolos mostrar en el listado detallado (el resumen
            por categoría siempre incluye el total completo).
    """
    if not mt5.initialize():
        print(f"initialize() falló. Código: {mt5.last_error()}")
        return

    try:
        rows = _collect_symbols(filter_pattern)
        if not rows:
            print("No se obtuvieron símbolos. ¿Está el terminal conectado?")
            return

        header = "=== Símbolos disponibles ==="
        if filter_pattern:
            header += f" (filtro: {filter_pattern})"
        print(header)

        _print_summary(rows)
        _print_listing(rows, limit)
    finally:
        mt5.shutdown()
