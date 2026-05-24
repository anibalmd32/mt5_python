"""Gráfico interactivo de velas con indicadores básicos.

Descarga histórico de MT5 (igual que s5), calcula uno o varios indicadores
sencillos sobre el precio de cierre, y dibuja un gráfico interactivo en el
navegador con Plotly. Permite hacer zoom, hover sobre cualquier vela para
ver los valores OHLC, y comparar visualmente el precio con los indicadores.

Indicadores soportados (en este nivel solo medias móviles):
- SMA<N>  → Simple Moving Average de N períodos. Promedio aritmético de
            los últimos N cierres. Suaviza el ruido. Si el precio está por
            encima de su SMA, tendencia alcista; por debajo, bajista.
- EMA<N>  → Exponential Moving Average de N períodos. Igual que SMA pero
            da más peso a los valores recientes; reacciona más rápido a
            los giros de tendencia.

Los N habituales: 20 (corto plazo), 50 (medio), 200 (largo).
"""

from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd
import plotly.graph_objects as go


SUPPORTED_TIMEFRAMES = ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1")

# Indicador → función que recibe DataFrame y devuelve Serie (alineada al df).
SUPPORTED_INDICATORS: dict[str, callable] = {
    "SMA20":  lambda df: df["close"].rolling(window=20).mean(),
    "SMA50":  lambda df: df["close"].rolling(window=50).mean(),
    "SMA200": lambda df: df["close"].rolling(window=200).mean(),
    "EMA20":  lambda df: df["close"].ewm(span=20, adjust=False).mean(),
    "EMA50":  lambda df: df["close"].ewm(span=50, adjust=False).mean(),
}


def _resolve_timeframe(name: str) -> int:
    upper = name.upper()
    if upper not in SUPPORTED_TIMEFRAMES:
        raise ValueError(
            f"Timeframe '{name}' no soportado. Usa uno de: {', '.join(SUPPORTED_TIMEFRAMES)}"
        )
    return getattr(mt5, f"TIMEFRAME_{upper}")


def _rates_to_dataframe(rates) -> pd.DataFrame:
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.rename(columns={"tick_volume": "volume"})
    return df[["time", "open", "high", "low", "close", "volume", "spread"]]


def _add_indicators(df: pd.DataFrame, indicators: tuple[str, ...]) -> pd.DataFrame:
    """Añade columnas al DataFrame, una por indicador."""
    for ind in indicators:
        if ind not in SUPPORTED_INDICATORS:
            raise ValueError(
                f"Indicador '{ind}' no soportado. Usa uno de: {', '.join(SUPPORTED_INDICATORS)}"
            )
    out = df.copy()
    for ind in indicators:
        out[ind] = SUPPORTED_INDICATORS[ind](out)
    return out


def _build_figure(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    indicators: tuple[str, ...],
) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df["time"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="OHLC",
            )
        ]
    )
    for ind in indicators:
        fig.add_trace(
            go.Scatter(
                x=df["time"],
                y=df[ind],
                mode="lines",
                name=ind,
            )
        )
    fig.update_layout(
        title=f"{symbol} · {timeframe.upper()} · últimas {len(df)} velas",
        xaxis_title="Tiempo (UTC del servidor)",
        yaxis_title="Precio",
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )
    # Saltar fines de semana (no hay velas → evita gaps feos)
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    return fig


def run(
    symbol: str = "EURUSD",
    timeframe: str = "H1",
    count: int = 300,
    indicators: tuple[str, ...] = ("SMA20", "SMA50"),
    show: bool = True,
    output_html: str | Path | None = None,
) -> Path | None:
    """Descarga histórico y dibuja gráfico interactivo de velas + indicadores.

    Args:
        symbol: instrumento (ej. "EURUSD").
        timeframe: temporalidad (M1..MN1).
        count: cuántas velas mostrar. Si pides SMA50, necesitas ≥50 para
            que la línea sea visible (las primeras 49 son NaN).
        indicators: tupla de indicadores a superponer. Ver SUPPORTED_INDICATORS.
        show: si True, abre el gráfico en el navegador.
        output_html: si se indica, también lo guarda como fichero HTML
            autocontenido (puedes abrirlo más tarde o compartirlo).

    Returns:
        Path al HTML guardado si `output_html` se indicó, si no None.

    Raises:
        ValueError: si timeframe o algún indicador no son válidos.
    """
    # Validar antes de tocar MT5 — fallar rápido si los parámetros son inválidos
    _resolve_timeframe(timeframe)
    for ind in indicators:
        if ind not in SUPPORTED_INDICATORS:
            raise ValueError(
                f"Indicador '{ind}' no soportado. Usa uno de: {', '.join(SUPPORTED_INDICATORS)}"
            )

    if not mt5.initialize():
        print(f"initialize() falló. Código: {mt5.last_error()}")
        return None

    try:
        if not mt5.symbol_select(symbol, True):
            print(f"No se pudo activar el símbolo '{symbol}'. Código: {mt5.last_error()}")
            return None

        tf = _resolve_timeframe(timeframe)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None or len(rates) == 0:
            print(f"No se obtuvieron datos para {symbol} {timeframe}. Código: {mt5.last_error()}")
            return None

        df = _rates_to_dataframe(rates)
        df = _add_indicators(df, indicators)
        fig = _build_figure(df, symbol, timeframe, indicators)

        saved: Path | None = None
        if output_html is not None:
            saved = Path(output_html)
            saved.parent.mkdir(parents=True, exist_ok=True)
            fig.write_html(str(saved))
            print(f"Gráfico guardado en: {saved.resolve()}")

        if show:
            print(f"Abriendo gráfico de {symbol} {timeframe.upper()} en el navegador...")
            fig.show()

        return saved
    finally:
        mt5.shutdown()
