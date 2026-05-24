from datetime import datetime, timezone

import pandas as pd
import pytest

from src.labs.nivel_2_datos import s6_tick_downloader as script
from tests.helpers import build_ticks_array


MT5_PATH = "src.labs.nivel_2_datos.s6_tick_downloader.mt5"
UTC = timezone.utc


@pytest.fixture
def mt5_mock(mocker):
    mt5 = mocker.patch(MT5_PATH)
    mt5.initialize.return_value = True
    mt5.last_error.return_value = (0, "ok")
    mt5.symbol_select.return_value = True
    mt5.copy_ticks_range.return_value = build_ticks_array(n=5)
    # Sentinels distintos para verificar que cada flag mapea bien
    mt5.COPY_TICKS_ALL = 1
    mt5.COPY_TICKS_INFO = 2
    mt5.COPY_TICKS_TRADE = 4
    return mt5


# --- _resolve_flags ---

def test_resolve_flags_returns_mt5_constant(mocker):
    mt5 = mocker.patch(MT5_PATH)
    mt5.COPY_TICKS_ALL = 1
    assert script._resolve_flags("all") == 1


def test_resolve_flags_case_insensitive(mocker):
    mt5 = mocker.patch(MT5_PATH)
    mt5.COPY_TICKS_INFO = 2
    assert script._resolve_flags("INFO") == 2


def test_resolve_flags_invalid_raises():
    with pytest.raises(ValueError, match="no soportado"):
        script._resolve_flags("garbage")


# --- _ticks_to_dataframe ---

def test_ticks_to_dataframe_has_expected_columns():
    df = script._ticks_to_dataframe(build_ticks_array(n=3))
    assert list(df.columns) == ["time", "bid", "ask", "last", "volume", "flags"]


def test_ticks_to_dataframe_time_is_datetime():
    df = script._ticks_to_dataframe(build_ticks_array(n=3))
    assert pd.api.types.is_datetime64_any_dtype(df["time"])


def test_ticks_to_dataframe_preserves_row_count():
    df = script._ticks_to_dataframe(build_ticks_array(n=7))
    assert len(df) == 7


def test_ticks_to_dataframe_uses_millisecond_precision():
    # build_ticks_array separa cada tick 100ms; verifico que ese delta sobrevive.
    df = script._ticks_to_dataframe(build_ticks_array(n=3))
    delta_ms = (df["time"].iloc[1] - df["time"].iloc[0]).total_seconds() * 1000
    assert delta_ms == 100


# --- run(): validaciones ---

def test_invalid_format_raises():
    with pytest.raises(ValueError, match="Formato"):
        script.run(output_format="xml")


def test_invalid_flags_raises():
    with pytest.raises(ValueError, match="Flag"):
        script.run(flags="garbage")


# --- run(): errores MT5 ---

def test_initialize_failure_returns_none(mocker, capsys):
    mt5 = mocker.patch(MT5_PATH)
    mt5.initialize.return_value = False
    mt5.last_error.return_value = (-1, "fail")
    mt5.COPY_TICKS_ALL = 1

    result = script.run()

    assert result is None
    assert "initialize() falló" in capsys.readouterr().out
    mt5.copy_ticks_range.assert_not_called()


def test_symbol_select_failure_returns_none(mt5_mock, capsys, tmp_path):
    mt5_mock.symbol_select.return_value = False

    result = script.run(symbol="ZZZUSD", output_dir=str(tmp_path))

    assert result is None
    assert "No se pudo activar el símbolo 'ZZZUSD'" in capsys.readouterr().out
    mt5_mock.copy_ticks_range.assert_not_called()


def test_no_ticks_returns_none(mt5_mock, capsys, tmp_path):
    mt5_mock.copy_ticks_range.return_value = None

    result = script.run(output_dir=str(tmp_path))

    assert result is None
    assert "No se obtuvieron ticks" in capsys.readouterr().out


def test_empty_ticks_returns_none(mt5_mock, capsys, tmp_path):
    mt5_mock.copy_ticks_range.return_value = build_ticks_array(n=0)

    result = script.run(output_dir=str(tmp_path))

    assert result is None
    assert "No se obtuvieron ticks" in capsys.readouterr().out


# --- run(): camino feliz ---

def test_csv_file_is_written(mt5_mock, tmp_path):
    result = script.run(output_dir=str(tmp_path))
    assert result is not None
    assert result.exists()
    assert result.suffix == ".csv"


def test_csv_contents(mt5_mock, tmp_path):
    script.run(output_dir=str(tmp_path))
    csv_path = next(tmp_path.glob("*.csv"))
    df = pd.read_csv(csv_path)
    assert len(df) == 5
    assert list(df.columns) == ["time", "bid", "ask", "last", "volume", "flags"]


def test_filename_includes_symbol_flags_and_hours(mt5_mock, tmp_path):
    now = datetime(2026, 5, 23, 12, 0, tzinfo=UTC)
    result = script.run(
        symbol="USDJPY", hours_back=2.0, flags="all",
        output_dir=str(tmp_path), now_utc=now,
    )
    assert result.name == "USDJPY_ticks_all_2h_5.csv"


def test_filename_handles_fractional_hours(mt5_mock, tmp_path):
    result = script.run(hours_back=0.5, output_dir=str(tmp_path), now_utc=datetime(2026, 5, 23, 12, 0, tzinfo=UTC))
    assert "_0.5h_" in result.name


def test_copy_ticks_range_receives_correct_args(mt5_mock, tmp_path):
    now = datetime(2026, 5, 23, 12, 0, tzinfo=UTC)
    expected_start = datetime(2026, 5, 23, 10, 0, tzinfo=UTC)

    script.run(
        symbol="EURUSD", hours_back=2.0, flags="all",
        output_dir=str(tmp_path), now_utc=now,
    )

    mt5_mock.copy_ticks_range.assert_called_once_with("EURUSD", expected_start, now, 1)


def test_run_with_info_flag(mt5_mock, tmp_path):
    script.run(flags="info", output_dir=str(tmp_path))
    args, _ = mt5_mock.copy_ticks_range.call_args
    assert args[3] == 2  # COPY_TICKS_INFO sentinel


def test_run_with_trade_flag(mt5_mock, tmp_path):
    script.run(flags="trade", output_dir=str(tmp_path))
    args, _ = mt5_mock.copy_ticks_range.call_args
    assert args[3] == 4  # COPY_TICKS_TRADE sentinel


def test_naive_now_utc_treated_as_utc(mt5_mock, tmp_path):
    naive = datetime(2026, 5, 23, 12, 0)
    script.run(hours_back=1.0, output_dir=str(tmp_path), now_utc=naive)

    args, _ = mt5_mock.copy_ticks_range.call_args
    assert args[1].tzinfo == UTC
    assert args[2].tzinfo == UTC


def test_output_directory_created_if_missing(mt5_mock, tmp_path):
    nested = tmp_path / "a" / "b"
    assert not nested.exists()

    result = script.run(output_dir=str(nested))

    assert result is not None
    assert nested.exists()


def test_symbol_select_called_with_enable_true(mt5_mock, tmp_path):
    script.run(symbol="EURUSD", output_dir=str(tmp_path))
    mt5_mock.symbol_select.assert_called_once_with("EURUSD", True)


# --- shutdown contract ---

def test_shutdown_called_on_success(mt5_mock, tmp_path):
    script.run(output_dir=str(tmp_path))
    mt5_mock.shutdown.assert_called_once()


def test_shutdown_called_on_symbol_select_failure(mt5_mock, tmp_path):
    mt5_mock.symbol_select.return_value = False
    script.run(output_dir=str(tmp_path))
    mt5_mock.shutdown.assert_called_once()


def test_shutdown_called_on_exception(mt5_mock, tmp_path):
    mt5_mock.copy_ticks_range.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError):
        script.run(output_dir=str(tmp_path))

    mt5_mock.shutdown.assert_called_once()


def test_shutdown_not_called_when_initialize_fails(mocker):
    mt5 = mocker.patch(MT5_PATH)
    mt5.initialize.return_value = False
    mt5.last_error.return_value = (-1, "fail")
    mt5.COPY_TICKS_ALL = 1

    script.run()

    mt5.shutdown.assert_not_called()
