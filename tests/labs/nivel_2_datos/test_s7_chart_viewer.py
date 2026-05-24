import pandas as pd
import plotly.graph_objects as go
import pytest

from src.labs.nivel_2_datos import s7_chart_viewer as script
from tests.helpers import build_rates_array


MT5_PATH = "src.labs.nivel_2_datos.s7_chart_viewer.mt5"


@pytest.fixture
def mt5_mock(mocker):
    mt5 = mocker.patch(MT5_PATH)
    mt5.initialize.return_value = True
    mt5.last_error.return_value = (0, "ok")
    mt5.symbol_select.return_value = True
    # Generamos suficientes velas para que SMA20 sea visible al menos al final
    mt5.copy_rates_from_pos.return_value = build_rates_array(n=30)
    mt5.TIMEFRAME_H1 = 16385
    mt5.TIMEFRAME_M5 = 5
    return mt5


@pytest.fixture
def fig_show_mock(mocker):
    """Evita que fig.show() abra un navegador en los tests."""
    return mocker.patch.object(go.Figure, "show")


# --- _resolve_timeframe ---

def test_resolve_timeframe_valid(mocker):
    mt5 = mocker.patch(MT5_PATH)
    mt5.TIMEFRAME_H1 = 16385
    assert script._resolve_timeframe("H1") == 16385


def test_resolve_timeframe_case_insensitive(mocker):
    mt5 = mocker.patch(MT5_PATH)
    mt5.TIMEFRAME_M5 = 5
    assert script._resolve_timeframe("m5") == 5


def test_resolve_timeframe_invalid_raises():
    with pytest.raises(ValueError, match="no soportado"):
        script._resolve_timeframe("XYZ")


# --- _add_indicators ---

def test_add_indicators_adds_sma20_column():
    df = pd.DataFrame({"close": list(range(30))})
    result = script._add_indicators(df, ("SMA20",))
    assert "SMA20" in result.columns


def test_add_indicators_multiple():
    df = pd.DataFrame({"close": list(range(60))})
    result = script._add_indicators(df, ("SMA20", "SMA50"))
    assert "SMA20" in result.columns
    assert "SMA50" in result.columns


def test_add_indicators_invalid_raises():
    df = pd.DataFrame({"close": [1, 2, 3]})
    with pytest.raises(ValueError, match="no soportado"):
        script._add_indicators(df, ("FAKE",))


def test_sma20_has_nan_in_first_19_rows():
    df = pd.DataFrame({"close": list(range(30))})
    result = script._add_indicators(df, ("SMA20",))
    assert result["SMA20"].iloc[:19].isna().all()
    assert not result["SMA20"].iloc[19:].isna().any()


def test_sma20_value_is_correct():
    # Cierre lineal 0..29 → SMA20 en posición 19 = media(0..19) = 9.5
    df = pd.DataFrame({"close": list(range(30))})
    result = script._add_indicators(df, ("SMA20",))
    assert result["SMA20"].iloc[19] == 9.5


def test_ema_does_not_have_nan_in_initial_rows():
    df = pd.DataFrame({"close": list(range(30))})
    result = script._add_indicators(df, ("EMA20",))
    # EMA tiene valor desde la fila 0 (a diferencia de SMA)
    assert not result["EMA20"].isna().any()


def test_add_indicators_does_not_mutate_input():
    df = pd.DataFrame({"close": list(range(30))})
    script._add_indicators(df, ("SMA20",))
    assert "SMA20" not in df.columns


# --- _build_figure ---

def _sample_df(n: int = 30) -> pd.DataFrame:
    return pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC"),
        "open": [1.10 + i * 0.001 for i in range(n)],
        "high": [1.11 + i * 0.001 for i in range(n)],
        "low":  [1.09 + i * 0.001 for i in range(n)],
        "close":[1.105 + i * 0.001 for i in range(n)],
        "volume": [100] * n,
        "spread": [1] * n,
        "SMA20": [1.105 + i * 0.001 for i in range(n)],
    })


def test_build_figure_returns_figure():
    fig = script._build_figure(_sample_df(), "EURUSD", "H1", ("SMA20",))
    assert isinstance(fig, go.Figure)


def test_build_figure_has_candlestick_trace():
    fig = script._build_figure(_sample_df(), "EURUSD", "H1", ())
    types = [t.type for t in fig.data]
    assert "candlestick" in types


def test_build_figure_has_one_scatter_per_indicator():
    df = _sample_df()
    df["SMA50"] = df["close"]
    fig = script._build_figure(df, "EURUSD", "H1", ("SMA20", "SMA50"))
    scatter_traces = [t for t in fig.data if t.type == "scatter"]
    assert len(scatter_traces) == 2
    names = [t.name for t in scatter_traces]
    assert "SMA20" in names
    assert "SMA50" in names


def test_build_figure_title_includes_symbol_and_timeframe():
    fig = script._build_figure(_sample_df(), "USDJPY", "M5", ())
    assert "USDJPY" in fig.layout.title.text
    assert "M5" in fig.layout.title.text


# --- run(): validaciones tempranas ---

def test_invalid_timeframe_raises_before_mt5():
    with pytest.raises(ValueError, match="Timeframe"):
        script.run(timeframe="XYZ", show=False)


def test_invalid_indicator_raises_before_mt5():
    with pytest.raises(ValueError, match="Indicador"):
        script.run(indicators=("BAD",), show=False)


# --- run(): errores MT5 ---

def test_initialize_failure_returns_none(mocker, capsys, fig_show_mock):
    mt5 = mocker.patch(MT5_PATH)
    mt5.initialize.return_value = False
    mt5.last_error.return_value = (-1, "fail")
    mt5.TIMEFRAME_H1 = 16385

    result = script.run(show=False)

    assert result is None
    assert "initialize() falló" in capsys.readouterr().out


def test_symbol_select_failure_returns_none(mt5_mock, fig_show_mock, capsys):
    mt5_mock.symbol_select.return_value = False

    result = script.run(symbol="ZZZUSD", show=False)

    assert result is None
    assert "No se pudo activar el símbolo 'ZZZUSD'" in capsys.readouterr().out
    mt5_mock.copy_rates_from_pos.assert_not_called()


def test_no_rates_returns_none(mt5_mock, fig_show_mock, capsys):
    mt5_mock.copy_rates_from_pos.return_value = None

    result = script.run(show=False)

    assert result is None
    assert "No se obtuvieron datos" in capsys.readouterr().out


def test_empty_rates_returns_none(mt5_mock, fig_show_mock, capsys):
    mt5_mock.copy_rates_from_pos.return_value = build_rates_array(n=0)

    result = script.run(show=False)

    assert result is None


# --- run(): camino feliz ---

def test_run_returns_none_when_no_output_html(mt5_mock, fig_show_mock):
    result = script.run(show=False)
    assert result is None


def test_run_saves_html_when_output_specified(mt5_mock, fig_show_mock, tmp_path):
    out = tmp_path / "chart.html"
    result = script.run(show=False, output_html=str(out))
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 0


def test_output_html_creates_parent_directory(mt5_mock, fig_show_mock, tmp_path):
    nested = tmp_path / "subdir" / "chart.html"
    script.run(show=False, output_html=str(nested))
    assert nested.exists()


def test_show_true_calls_fig_show(mt5_mock, fig_show_mock):
    script.run(show=True)
    fig_show_mock.assert_called_once()


def test_show_false_does_not_call_fig_show(mt5_mock, fig_show_mock):
    script.run(show=False)
    fig_show_mock.assert_not_called()


def test_copy_rates_called_with_correct_args(mt5_mock, fig_show_mock):
    script.run(symbol="EURUSD", timeframe="H1", count=300, show=False)
    mt5_mock.copy_rates_from_pos.assert_called_once_with("EURUSD", 16385, 0, 300)


# --- shutdown contract ---

def test_shutdown_called_on_success(mt5_mock, fig_show_mock):
    script.run(show=False)
    mt5_mock.shutdown.assert_called_once()


def test_shutdown_called_on_exception(mt5_mock, fig_show_mock):
    mt5_mock.copy_rates_from_pos.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError):
        script.run(show=False)

    mt5_mock.shutdown.assert_called_once()


def test_shutdown_not_called_when_initialize_fails(mocker, fig_show_mock):
    mt5 = mocker.patch(MT5_PATH)
    mt5.initialize.return_value = False
    mt5.last_error.return_value = (-1, "fail")
    mt5.TIMEFRAME_H1 = 16385

    script.run(show=False)

    mt5.shutdown.assert_not_called()
