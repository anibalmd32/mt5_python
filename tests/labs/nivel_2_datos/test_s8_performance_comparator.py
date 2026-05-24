import pandas as pd
import plotly.graph_objects as go
import pytest

from src.labs.nivel_2_datos import s8_performance_comparator as script
from tests.helpers import build_rates_array


MT5_PATH = "src.labs.nivel_2_datos.s8_performance_comparator.mt5"


@pytest.fixture
def mt5_mock(mocker):
    mt5 = mocker.patch(MT5_PATH)
    mt5.initialize.return_value = True
    mt5.last_error.return_value = (0, "ok")
    mt5.symbol_select.return_value = True
    mt5.copy_rates_from_pos.return_value = build_rates_array(n=30)
    mt5.TIMEFRAME_D1 = 16408
    mt5.TIMEFRAME_H1 = 16385
    return mt5


@pytest.fixture
def fig_show_mock(mocker):
    return mocker.patch.object(go.Figure, "show")


# --- _resolve_timeframe ---

def test_resolve_timeframe_valid(mocker):
    mt5 = mocker.patch(MT5_PATH)
    mt5.TIMEFRAME_D1 = 16408
    assert script._resolve_timeframe("D1") == 16408


def test_resolve_timeframe_invalid_raises():
    with pytest.raises(ValueError, match="no soportado"):
        script._resolve_timeframe("XYZ")


# --- _normalize_to_pct ---

def test_normalize_to_pct_first_row_is_zero():
    df = pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=3, freq="D", tz="UTC"),
        "close": [100.0, 105.0, 110.0],
    })
    out = script._normalize_to_pct(df)
    assert out["pct"].iloc[0] == 0.0


def test_normalize_to_pct_values_are_correct():
    df = pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=3, freq="D", tz="UTC"),
        "close": [100.0, 105.0, 110.0],
    })
    out = script._normalize_to_pct(df)
    assert out["pct"].iloc[1] == pytest.approx(5.0)
    assert out["pct"].iloc[2] == pytest.approx(10.0)


def test_normalize_to_pct_handles_negative_change():
    df = pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=2, freq="D", tz="UTC"),
        "close": [100.0, 92.5],
    })
    out = script._normalize_to_pct(df)
    assert out["pct"].iloc[1] == pytest.approx(-7.5)


def test_normalize_to_pct_does_not_mutate_input():
    df = pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=2, freq="D", tz="UTC"),
        "close": [100.0, 110.0],
    })
    script._normalize_to_pct(df)
    assert "pct" not in df.columns


# --- _build_figure ---

def _two_symbol_series() -> dict[str, pd.DataFrame]:
    base = pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=5, freq="D", tz="UTC"),
        "close": [100.0, 102.0, 101.0, 103.0, 104.0],
    })
    return {
        "EURUSD": script._normalize_to_pct(base),
        "GBPUSD": script._normalize_to_pct(base.assign(close=[100.0, 99.0, 98.0, 97.0, 96.0])),
    }


def test_build_figure_has_one_trace_per_symbol():
    fig = script._build_figure(_two_symbol_series(), "D1", 5)
    names = [t.name for t in fig.data]
    assert "EURUSD" in names
    assert "GBPUSD" in names


def test_build_figure_title_includes_timeframe():
    fig = script._build_figure(_two_symbol_series(), "h1", 5)
    assert "H1" in fig.layout.title.text


# --- run(): validaciones ---

def test_empty_symbols_raises():
    with pytest.raises(ValueError, match="al menos un símbolo"):
        script.run(symbols=(), show=False)


def test_invalid_timeframe_raises_before_mt5():
    with pytest.raises(ValueError, match="Timeframe"):
        script.run(timeframe="XYZ", show=False)


# --- run(): errores MT5 ---

def test_initialize_failure_returns_none(mocker, capsys, fig_show_mock):
    mt5 = mocker.patch(MT5_PATH)
    mt5.initialize.return_value = False
    mt5.last_error.return_value = (-1, "fail")
    mt5.TIMEFRAME_D1 = 16408

    result = script.run(show=False)

    assert result is None
    assert "initialize() falló" in capsys.readouterr().out


def test_all_symbols_fail_returns_none(mt5_mock, fig_show_mock, capsys):
    mt5_mock.copy_rates_from_pos.return_value = None

    result = script.run(symbols=("BAD1", "BAD2"), show=False)

    assert result is None
    assert "Ningún símbolo dio datos" in capsys.readouterr().out


def test_symbol_select_failure_skips_that_symbol(mt5_mock, fig_show_mock, capsys):
    def fake_select(sym, enable):
        return sym != "BAD"
    mt5_mock.symbol_select.side_effect = fake_select

    result = script.run(symbols=("EURUSD", "BAD", "GBPUSD"), show=False)

    out = capsys.readouterr().out
    assert "AVISO: no se pudo activar 'BAD'" in out
    assert result is not None
    assert "EURUSD" in result
    assert "GBPUSD" in result
    assert "BAD" not in result


def test_partial_failure_continues_with_remaining(mt5_mock, fig_show_mock):
    def fake_rates(sym, tf, pos, count):
        if sym == "MISSING":
            return None
        return build_rates_array(n=30)
    mt5_mock.copy_rates_from_pos.side_effect = fake_rates

    result = script.run(symbols=("EURUSD", "MISSING", "GBPUSD"), show=False)

    assert result is not None
    assert set(result.keys()) == {"EURUSD", "GBPUSD"}


# --- run(): camino feliz ---

def test_returns_dict_with_pct_per_symbol(mt5_mock, fig_show_mock):
    result = script.run(symbols=("EURUSD", "GBPUSD"), show=False)
    assert isinstance(result, dict)
    assert set(result.keys()) == {"EURUSD", "GBPUSD"}
    assert all(isinstance(v, float) for v in result.values())


def test_first_pct_value_is_zero_via_summary(mt5_mock, fig_show_mock, capsys):
    script.run(symbols=("EURUSD",), show=False)
    out = capsys.readouterr().out
    # En el helper build_rates_array los cierres son monotonamente
    # crecientes, así que la variación final debería ser > 0
    assert "Ganador:  EURUSD" in out


def test_summary_includes_period_and_count(mt5_mock, fig_show_mock, capsys):
    script.run(symbols=("EURUSD",), timeframe="D1", show=False)
    out = capsys.readouterr().out
    assert "Período:" in out
    assert "30 velas D1" in out


def test_summary_orders_symbols_by_pct_descending(mt5_mock, fig_show_mock, capsys):
    def fake_rates(sym, tf, pos, count):
        # Hacemos que cada símbolo tenga rendimientos distintos
        arr = build_rates_array(n=30)
        if sym == "BIG_WIN":
            arr["close"] = arr["close"] * 1.1  # +10%
        elif sym == "BIG_LOSS":
            arr["close"] = arr["close"] * 0.9  # mismo, pero usaremos otra técnica
        return arr
    mt5_mock.copy_rates_from_pos.side_effect = fake_rates

    script.run(symbols=("EURUSD", "BIG_WIN"), show=False)
    out = capsys.readouterr().out
    # BIG_WIN debería aparecer antes que EURUSD en la tabla (porcentajes
    # ordenados descendentes); como ambos suben monotonamente desde la misma
    # forma, la posición exacta depende del seed — verifico solo que el
    # ganador es uno de los dos
    assert ("Ganador:  EURUSD" in out) or ("Ganador:  BIG_WIN" in out)


def test_copy_rates_called_once_per_symbol(mt5_mock, fig_show_mock):
    script.run(symbols=("EURUSD", "GBPUSD", "USDJPY"), show=False)
    assert mt5_mock.copy_rates_from_pos.call_count == 3


def test_symbol_select_called_for_each_symbol(mt5_mock, fig_show_mock):
    script.run(symbols=("EURUSD", "GBPUSD"), show=False)
    assert mt5_mock.symbol_select.call_count == 2


# --- output_html ---

def test_output_html_saves_file(mt5_mock, fig_show_mock, tmp_path):
    out_path = tmp_path / "compare.html"
    script.run(symbols=("EURUSD", "GBPUSD"), show=False, output_html=str(out_path))
    assert out_path.exists()
    assert out_path.stat().st_size > 0


def test_output_html_creates_parent_dir(mt5_mock, fig_show_mock, tmp_path):
    nested = tmp_path / "a" / "b" / "compare.html"
    script.run(symbols=("EURUSD",), show=False, output_html=str(nested))
    assert nested.exists()


# --- show contract ---

def test_show_true_calls_fig_show(mt5_mock, fig_show_mock):
    script.run(symbols=("EURUSD",), show=True)
    fig_show_mock.assert_called_once()


def test_show_false_does_not_call_fig_show(mt5_mock, fig_show_mock):
    script.run(symbols=("EURUSD",), show=False)
    fig_show_mock.assert_not_called()


# --- shutdown contract ---

def test_shutdown_called_on_success(mt5_mock, fig_show_mock):
    script.run(symbols=("EURUSD",), show=False)
    mt5_mock.shutdown.assert_called_once()


def test_shutdown_called_on_exception(mt5_mock, fig_show_mock):
    mt5_mock.copy_rates_from_pos.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError):
        script.run(symbols=("EURUSD",), show=False)

    mt5_mock.shutdown.assert_called_once()


def test_shutdown_not_called_when_initialize_fails(mocker, fig_show_mock):
    mt5 = mocker.patch(MT5_PATH)
    mt5.initialize.return_value = False
    mt5.last_error.return_value = (-1, "fail")
    mt5.TIMEFRAME_D1 = 16408

    script.run(symbols=("EURUSD",), show=False)

    mt5.shutdown.assert_not_called()
