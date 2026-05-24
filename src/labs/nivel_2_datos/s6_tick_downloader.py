"""Descarga ticks (operación a operación) desde MT5 y los guarda a disco.

¿Qué es un tick?
================
Un tick es la unidad MÍNIMA de información de precio: cada vez que el
bid o el ask cambian, se genera un tick. En periodos activos (overlap
Londres-NY en EUR/USD, por ejemplo) puede haber varios ticks por
segundo. Cada tick lleva milisegundo de precisión.

Comparado con una vela:
- Una vela H1 resume "lo que pasó en una hora" en 4 números (OHLC).
- Esa misma hora puede contener 5.000-30.000 ticks individuales.
- Los ticks contienen TODOS los movimientos, las velas solo los extremos.

Campos de un tick:
- bid          → precio al que el broker te compra (tú vendes a ese precio)
- ask          → precio al que el broker te vende (tú compras a ese precio)
- last         → último precio negociado realmente (en FX casi siempre 0;
                 relevante para futuros y acciones)
- volume       → número de operaciones en este tick (en FX es "tick volume")
- time_msc     → timestamp en milisegundos (más preciso que `time` en segundos)
- flags        → bitfield indicando qué cambió: bid=2, ask=4, last=8, etc.

¿Cuándo usar ticks en lugar de velas?
- Análisis del spread y su variación intra-vela.
- Estudio de slippage y ejecución.
- Backtesting de scalping o HFT.
- Construcción de "barras alternativas": Renko, range bars, volume bars.

Para análisis "normal" de tendencia o señales, los ticks son matar moscas
a cañonazos: usa `s5_history_downloader` con la temporalidad adecuada.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd


SUPPORTED_FORMATS = ("csv", "parquet")

# Mapeo nombre amigable → constante MT5. Resuelvo getattr en runtime para
# que los tests puedan mockear el módulo.
SUPPORTED_FLAGS = {
    "all":   "COPY_TICKS_ALL",    # todo (recomendado)
    "info":  "COPY_TICKS_INFO",   # solo cambios de bid/ask (cotizaciones)
    "trade": "COPY_TICKS_TRADE",  # solo transacciones ejecutadas
}


def _resolve_flags(name: str) -> int:
    key = name.lower()
    if key not in SUPPORTED_FLAGS:
        raise ValueError(
            f"Flag '{name}' no soportado. Usa uno de: {', '.join(SUPPORTED_FLAGS.keys())}"
        )
    return getattr(mt5, SUPPORTED_FLAGS[key])


def _ticks_to_dataframe(ticks) -> pd.DataFrame:
    """Convierte el numpy structured array de ticks en DataFrame legible.

    Uso `time_msc` (milisegundos) como timestamp principal porque la milésima
    sí importa cuando hay decenas de ticks por segundo.
    """
    df = pd.DataFrame(ticks)
    df["time"] = pd.to_datetime(df["time_msc"], unit="ms", utc=True)
    return df[["time", "bid", "ask", "last", "volume", "flags"]]


def _save(df: pd.DataFrame, path: Path, fmt: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "csv":
        df.to_csv(path, index=False)
    elif fmt == "parquet":
        try:
            df.to_parquet(path, index=False)
        except ImportError as e:
            raise ImportError(
                "El formato parquet requiere 'pyarrow' o 'fastparquet'. "
                "Instálalo con: pip install pyarrow"
            ) from e
    else:
        raise ValueError(f"Formato '{fmt}' no soportado.")


def run(
    symbol: str = "EURUSD",
    hours_back: float = 1.0,
    flags: str = "all",
    output_dir: str = "data",
    output_format: str = "csv",
    now_utc: datetime | None = None,
) -> Path | None:
    """Descarga los ticks de `symbol` de las últimas `hours_back` horas.

    Args:
        symbol: instrumento (ej. "EURUSD").
        hours_back: ventana hacia atrás desde `now_utc`. Soporta decimales
            (0.5 = 30 minutos). Cuidado con valores grandes en pares líquidos:
            1 día de EURUSD ticks puede ser ~500.000 filas y varios MB.
        flags: "all" (todo), "info" (solo cotizaciones bid/ask) o "trade"
            (solo ejecuciones reales — devuelve vacío en FX).
        output_dir: carpeta destino (se crea si no existe).
        output_format: "csv" o "parquet".
        now_utc: instante "fin" de la ventana (tz-aware). None = ahora.
            Útil para tests y para pedir una ventana histórica concreta.

    Returns:
        Path al fichero creado, o None si hubo error de MT5.

    Raises:
        ValueError: si el formato o el flag son inválidos.
    """
    fmt = output_format.lower()
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Formato '{output_format}' no soportado. Usa: {', '.join(SUPPORTED_FORMATS)}"
        )

    flag_name = flags.lower()
    flag_const = _resolve_flags(flag_name)

    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    elif now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    start = now_utc - timedelta(hours=hours_back)

    if not mt5.initialize():
        print(f"initialize() falló. Código: {mt5.last_error()}")
        return None

    try:
        if not mt5.symbol_select(symbol, True):
            print(f"No se pudo activar el símbolo '{symbol}'. Código: {mt5.last_error()}")
            return None

        ticks = mt5.copy_ticks_range(symbol, start, now_utc, flag_const)
        if ticks is None or len(ticks) == 0:
            print(
                f"No se obtuvieron ticks para {symbol} en las últimas {hours_back}h. "
                f"Código: {mt5.last_error()}"
            )
            return None

        df = _ticks_to_dataframe(ticks)

        hours_str = f"{hours_back:g}h"
        filename = f"{symbol}_ticks_{flag_name}_{hours_str}_{len(df)}.{fmt}"
        path = Path(output_dir) / filename
        _save(df, path, fmt)

        print(f"Descargados {len(df):,} ticks de {symbol} (flags={flag_name}, {hours_str})")
        print(f"  Período: {df['time'].iloc[0]} → {df['time'].iloc[-1]}")
        print(f"  Guardado en: {path.resolve()}")

        return path
    finally:
        mt5.shutdown()
