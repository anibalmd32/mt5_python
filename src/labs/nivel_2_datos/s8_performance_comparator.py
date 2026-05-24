"""Compara el rendimiento porcentual de varios símbolos en el mismo período.

Útil para responder rápido a preguntas como:
- ¿Qué subió más este mes? ¿EUR/USD, GBP/USD o el oro?
- ¿Se han movido juntos los pares JPY esta semana?
- ¿Cómo se compara el S&P500 con el Nasdaq en lo que va de año?

La idea es **normalizar cada serie a su primer cierre y mostrar la variación
porcentual relativa**. Así un par cotizado a 1.10 y un índice cotizado a
4500 se ven en la misma escala (% acumulado), y un movimiento del 1% se ve
igual de grande en ambos.
"""

from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd
import plotly.graph_objects as go


SUPPORTED_TIMEFRAMES = ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1")


def _resolve_timeframe(name: str) -> int:
    upper = name.upper()
    if upper not in SUPPORTED_TIMEFRAMES:
        raise ValueError(
            f"Timeframe '{name}' no soportado. Usa uno de: {', '.join(SUPPORTED_TIMEFRAMES)}"
        )
    return getattr(mt5, f"TIMEFRAME_{upper}")


def _fetch_close_series(symbol: str, tf_const: int, count: int) -> pd.DataFrame | None:
    """Activa el símbolo, baja sus velas y devuelve DataFrame[time, close].

    Devuelve None si el símbolo no se pudo activar o no devolvió datos. La
    estrategia es "best-effort": un símbolo malo no aborta toda la comparativa.
    """
    if not mt5.symbol_select(symbol, True):
        print(f"  AVISO: no se pudo activar '{symbol}', se omite.")
        return None
    rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, count)
    if rates is None or len(rates) == 0:
        print(f"  AVISO: sin datos para '{symbol}', se omite.")
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    return df[["time", "close"]]


def _normalize_to_pct(df: pd.DataFrame) -> pd.DataFrame:
    """Añade columna `pct`: variación porcentual desde el primer cierre.

    Primera fila siempre 0%. Una subida del 1% sobre el primer precio sale
    como +1.0 (no 0.01).
    """
    out = df.copy()
    base = out["close"].iloc[0]
    out["pct"] = (out["close"] / base - 1) * 100
    return out


def _print_summary(series_by_symbol: dict[str, pd.DataFrame], timeframe: str) -> None:
    finals = {sym: df["pct"].iloc[-1] for sym, df in series_by_symbol.items()}
    first_sym = next(iter(series_by_symbol))
    df_first = series_by_symbol[first_sym]

    print("\n=== Comparador de rendimiento ===")
    print(
        f"  Período: {df_first['time'].iloc[0]} -> {df_first['time'].iloc[-1]}  "
        f"({len(df_first)} velas {timeframe.upper()})"
    )
    print()
    print(f"  {'Símbolo':<10} {'Variación':>12}")
    print("  " + "-" * 24)
    for sym in sorted(finals, key=finals.get, reverse=True):
        print(f"  {sym:<10} {finals[sym]:>+11.2f} %")
    print()
    winner = max(finals, key=finals.get)
    loser = min(finals, key=finals.get)
    print(f"  Ganador:  {winner}  ({finals[winner]:+.2f} %)")
    print(f"  Perdedor: {loser}  ({finals[loser]:+.2f} %)")


def _build_figure(
    series_by_symbol: dict[str, pd.DataFrame],
    timeframe: str,
    count: int,
) -> go.Figure:
    fig = go.Figure()
    for sym, df in series_by_symbol.items():
        fig.add_trace(
            go.Scatter(
                x=df["time"],
                y=df["pct"],
                mode="lines",
                name=sym,
            )
        )
    fig.update_layout(
        title=f"Rendimiento comparado · {timeframe.upper()} · últimas {count} velas",
        xaxis_title="Tiempo (UTC del servidor)",
        yaxis_title="Variación acumulada (%)",
        hovermode="x unified",
    )
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    # Línea de referencia en 0% (donde empezaron todos)
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    return fig


def run(
    symbols: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDJPY"),
    timeframe: str = "D1",
    count: int = 30,
    show: bool = True,
    output_html: str | Path | None = None,
) -> dict[str, float] | None:
    """Compara la variación porcentual de varios símbolos en el mismo período.

    Args:
        symbols: tupla de símbolos a comparar. Debe contener al menos uno.
        timeframe: temporalidad común para todos.
        count: cuántas velas (igual para todos).
        show: si True, abre la comparativa en el navegador.
        output_html: si se indica, guarda el gráfico como fichero HTML.

    Returns:
        Dict `{símbolo: variación_final_pct}` para los símbolos que funcionaron,
        o None si ninguno dio datos.

    Raises:
        ValueError: si `symbols` está vacío o el timeframe no es válido.
    """
    if not symbols:
        raise ValueError("Debes indicar al menos un símbolo en `symbols`.")

    _resolve_timeframe(timeframe)  # valida antes de tocar MT5

    if not mt5.initialize():
        print(f"initialize() falló. Código: {mt5.last_error()}")
        return None

    try:
        tf = _resolve_timeframe(timeframe)
        series: dict[str, pd.DataFrame] = {}

        for sym in symbols:
            df = _fetch_close_series(sym, tf, count)
            if df is None:
                continue
            series[sym] = _normalize_to_pct(df)

        if not series:
            print("Ningún símbolo dio datos.")
            return None

        _print_summary(series, timeframe)

        fig = _build_figure(series, timeframe, count)

        saved: Path | None = None
        if output_html is not None:
            saved = Path(output_html)
            saved.parent.mkdir(parents=True, exist_ok=True)
            fig.write_html(str(saved))
            print(f"  Gráfico guardado en: {saved.resolve()}")

        if show:
            print("  Abriendo comparativa en el navegador...")
            fig.show()

        return {sym: df["pct"].iloc[-1] for sym, df in series.items()}

    finally:
        mt5.shutdown()
