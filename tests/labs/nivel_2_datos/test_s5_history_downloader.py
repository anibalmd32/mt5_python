from pathlib import Path

import pandas as pd
import pytest

from src.labs.nivel_2_datos import s5_history_downloader as script
from tests.helpers import build_rates_array


MT5_PATH = "src.labs.nivel_2_datos.s5_history_downloader.mt5"


@pytest.fixture
def mt5_mock(mocker):
    mt5 = mocker.patch(MT5_PATH)
    mt5.initialize.return_value = True
    mt5.last_error.return_value = (0, "ok")
    mt5.symbol_select.return_value = True
    mt5.copy_rates_from_pos.return_value = build_rates_array(n=5)
    # Sentinel para verificar que se pasa la constante correcta
    mt5.TIMEFRAME_H1 = 16385
    mt5.TIMEFRAME_M5 = 5
    mt5.TIMEFRAME_D1 = 16408
    return mt5


# --- _resolve_timeframe ---

def test_resolve_timeframe_returns_mt5_constant(mocker):
    mt5 = mocker.patch(MT5_PATH)
    mt5.TIMEFRAME_H1 = 16385
    assert script._resolve_timeframe("H1") == 16385


def test_resolve_timeframe_is_case_insensitive(mocker):
    mt5 = mocker.patch(MT5_PATH)
    mt5.TIMEFRAME_M5 = 5
    assert script._resolve_timeframe("m5") == 5


def test_resolve_timeframe_invalid_raises():
    with pytest.raises(ValueError, match="no soportado"):
        script._resolve_timeframe("XYZ")


# --- _rates_to_dataframe ---

def test_rates_to_dataframe_has_expected_columns():
    rates = build_rates_array(n=3)
    df = script._rates_to_dataframe(rates)
    assert list(df.columns) == ["time", "open", "high", "low", "close", "volume", "spread"]


def test_rates_to_dataframe_converts_time_to_datetime():
    rates = build_rates_array(n=3)
    df = script._rates_to_dataframe(rates)
    assert pd.api.types.is_datetime64_any_dtype(df["time"])


def test_rates_to_dataframe_renames_tick_volume_to_volume():
    rates = build_rates_array(n=3)
    df = script._rates_to_dataframe(rates)
    assert "volume" in df.columns
    assert "tick_volume" not in df.columns


def test_rates_to_dataframe_preserves_row_count():
    rates = build_rates_array(n=7)
    df = script._rates_to_dataframe(rates)
    assert len(df) == 7


# --- run(): validaciones de parámetros ---

def test_invalid_format_raises():
    with pytest.raises(ValueError, match="Formato"):
        script.run(output_format="xml")


def test_invalid_timeframe_raises():
    with pytest.raises(ValueError, match="Timeframe"):
        script.run(timeframe="XYZ")


# --- run(): manejo de errores de MT5 ---

def test_initialize_failure_returns_none(mocker, capsys):
    mt5 = mocker.patch(MT5_PATH)
    mt5.initialize.return_value = False
    mt5.last_error.return_value = (-1, "fail")
    mt5.TIMEFRAME_H1 = 16385

    result = script.run()

    assert result is None
    assert "initialize() falló" in capsys.readouterr().out
    mt5.copy_rates_from_pos.assert_not_called()


def test_symbol_select_failure_returns_none(mt5_mock, capsys, tmp_path):
    mt5_mock.symbol_select.return_value = False

    result = script.run(symbol="ZZZUSD", output_dir=str(tmp_path))

    assert result is None
    assert "No se pudo activar el símbolo 'ZZZUSD'" in capsys.readouterr().out
    mt5_mock.copy_rates_from_pos.assert_not_called()


def test_no_rates_returned_returns_none(mt5_mock, capsys, tmp_path):
    mt5_mock.copy_rates_from_pos.return_value = None

    result = script.run(output_dir=str(tmp_path))

    assert result is None
    assert "No se obtuvieron datos" in capsys.readouterr().out


def test_empty_rates_returned_returns_none(mt5_mock, capsys, tmp_path):
    mt5_mock.copy_rates_from_pos.return_value = build_rates_array(n=0)

    result = script.run(output_dir=str(tmp_path))

    assert result is None
    assert "No se obtuvieron datos" in capsys.readouterr().out


# --- run(): camino feliz ---

def test_csv_file_is_written(mt5_mock, tmp_path):
    result = script.run(symbol="EURUSD", timeframe="H1", count=5, output_dir=str(tmp_path))

    assert result is not None
    assert result.exists()
    assert result.suffix == ".csv"


def test_csv_file_contents_match_input(mt5_mock, tmp_path):
    script.run(symbol="EURUSD", timeframe="H1", count=5, output_dir=str(tmp_path))

    csv_path = next(tmp_path.glob("*.csv"))
    df = pd.read_csv(csv_path)
    assert len(df) == 5
    assert list(df.columns) == ["time", "open", "high", "low", "close", "volume", "spread"]


def test_filename_format(mt5_mock, tmp_path):
    result = script.run(symbol="USDJPY", timeframe="M5", count=5, output_dir=str(tmp_path))

    assert result.name == "USDJPY_M5_5velas.csv"


def test_output_directory_created_if_missing(mt5_mock, tmp_path):
    nested = tmp_path / "subdir" / "extra"
    assert not nested.exists()

    result = script.run(output_dir=str(nested))

    assert result is not None
    assert nested.exists()


def test_copy_rates_from_pos_receives_correct_args(mt5_mock, tmp_path):
    script.run(symbol="EURUSD", timeframe="H1", count=500, output_dir=str(tmp_path))

    mt5_mock.copy_rates_from_pos.assert_called_once_with("EURUSD", 16385, 0, 500)


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
    mt5_mock.copy_rates_from_pos.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError):
        script.run(output_dir=str(tmp_path))

    mt5_mock.shutdown.assert_called_once()


def test_shutdown_not_called_when_initialize_fails(mocker):
    mt5 = mocker.patch(MT5_PATH)
    mt5.initialize.return_value = False
    mt5.last_error.return_value = (-1, "fail")
    mt5.TIMEFRAME_H1 = 16385

    script.run()

    mt5.shutdown.assert_not_called()
