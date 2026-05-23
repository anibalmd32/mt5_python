"""Descarga histórico de velas (OHLC) desde MT5 y lo guarda a disco.

¿Qué es una "vela"? Cada vela resume los precios de un período concreto en
cuatro números:
    Open  → precio al inicio del período
    High  → máximo alcanzado dentro del período
    Low   → mínimo alcanzado dentro del período
    Close → precio al final del período

Una temporalidad ("timeframe") es la duración de cada vela: M1=1 minuto,
H1=1 hora, D1=1 día, etc. Este script pide N velas recientes y las guarda
como CSV (universal, lo abre Excel) o Parquet (compacto, pensado para
análisis con pandas).
"""

from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd


SUPPORTED_TIMEFRAMES = ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1")
SUPPORTED_FORMATS = ("csv", "parquet")


def _resolve_timeframe(name: str) -> int:
    """Convierte 'H1' → mt5.TIMEFRAME_H1.

    Lo hago así (en lugar de un dict pre-cargado) para que la búsqueda ocurra
    en runtime, no en import. Esto permite que los tests mockeen mt5 y aún
    funcione.
    """
    upper = name.upper()
    if upper not in SUPPORTED_TIMEFRAMES:
        raise ValueError(
            f"Timeframe '{name}' no soportado. Usa uno de: {', '.join(SUPPORTED_TIMEFRAMES)}"
        )
    return getattr(mt5, f"TIMEFRAME_{upper}")


def _rates_to_dataframe(rates) -> pd.DataFrame:
    """Convierte el numpy structured array de MT5 en un DataFrame legible."""
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.rename(columns={"tick_volume": "volume"})
    return df[["time", "open", "high", "low", "close", "volume", "spread"]]


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
    timeframe: str = "H1",
    count: int = 1000,
    output_dir: str = "data",
    output_format: str = "csv",
) -> Path | None:
    """Descarga `count` velas recientes de `symbol` y las guarda en disco.

    Args:
        symbol: instrumento (ej. "EURUSD", "USDJPY").
        timeframe: temporalidad (ver SUPPORTED_TIMEFRAMES).
        count: cuántas velas pedir, empezando por la más reciente hacia atrás.
        output_dir: carpeta destino (se crea si no existe).
        output_format: "csv" o "parquet".

    Returns:
        Path al fichero creado, o None si hubo error de MT5.

    Raises:
        ValueError: si el timeframe o el formato no están soportados.
    """
    fmt = output_format.lower()
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Formato '{output_format}' no soportado. Usa: {', '.join(SUPPORTED_FORMATS)}"
        )

    tf_name = timeframe.upper()
    tf_const = _resolve_timeframe(tf_name)

    if not mt5.initialize():
        print(f"initialize() falló. Código: {mt5.last_error()}")
        return None

    try:
        if not mt5.symbol_select(symbol, True):
            print(f"No se pudo activar el símbolo '{symbol}'. Código: {mt5.last_error()}")
            return None

        rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, count)
        if rates is None or len(rates) == 0:
            print(f"No se obtuvieron datos para {symbol} {tf_name}. Código: {mt5.last_error()}")
            return None

        df = _rates_to_dataframe(rates)

        filename = f"{symbol}_{tf_name}_{len(df)}velas.{fmt}"
        path = Path(output_dir) / filename
        _save(df, path, fmt)

        print(f"Descargadas {len(df)} velas de {symbol} {tf_name}")
        print(f"  Período: {df['time'].iloc[0]} → {df['time'].iloc[-1]}")
        print(f"  Guardado en: {path.resolve()}")

        return path
    finally:
        mt5.shutdown()
