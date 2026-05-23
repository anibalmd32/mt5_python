import pytest

from src.labs.nivel_1_familiarizacion import s1_connection_check as script
from tests.helpers import (
    HEDGING_MODE,
    build_account_mock,
    build_terminal_mock,
    build_tick_mock,
)


MT5_PATH = "src.labs.nivel_1_familiarizacion.s1_connection_check.mt5"


@pytest.fixture
def mt5_mock(mocker):
    mt5 = mocker.patch(MT5_PATH)
    mt5.initialize.return_value = True
    mt5.last_error.return_value = (0, "No error")
    mt5.terminal_info.return_value = build_terminal_mock()
    mt5.account_info.return_value = build_account_mock()
    mt5.version.return_value = (500, 5836, "28 Apr 2026")
    mt5.symbol_info_tick.return_value = build_tick_mock()
    mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING = HEDGING_MODE
    return mt5


def test_initialize_failure_prints_error_and_returns(mocker, capsys):
    mt5 = mocker.patch(MT5_PATH)
    mt5.initialize.return_value = False
    mt5.last_error.return_value = (-10003, "IPC timeout")

    script.run()

    out = capsys.readouterr().out
    assert "initialize() falló" in out
    assert "-10003" in out
    mt5.terminal_info.assert_not_called()
    mt5.shutdown.assert_not_called()


def test_successful_run_prints_all_sections(mt5_mock, capsys):
    script.run()

    out = capsys.readouterr().out
    assert "=== Terminal ===" in out
    assert "=== Cuenta ===" in out
    assert "=== Último tick EURUSD ===" in out


def test_successful_run_includes_account_details(mt5_mock, capsys):
    script.run()

    out = capsys.readouterr().out
    assert "107401078" in out
    assert "MetaQuotes-Demo" in out
    assert "USD" in out
    assert "100000.0" in out
    assert "1:100" in out


def test_hedge_account_label(mt5_mock, capsys):
    script.run()
    assert "Tipo cuenta:  Hedge" in capsys.readouterr().out


def test_netting_account_label(mt5_mock, capsys):
    mt5_mock.account_info.return_value.margin_mode = 0

    script.run()

    assert "Tipo cuenta:  Otro" in capsys.readouterr().out


def test_custom_symbol_is_requested(mt5_mock, capsys):
    script.run("USDJPY")

    out = capsys.readouterr().out
    mt5_mock.symbol_info_tick.assert_called_once_with("USDJPY")
    assert "=== Último tick USDJPY ===" in out


def test_tick_none_prints_warning(mt5_mock, capsys):
    mt5_mock.symbol_info_tick.return_value = None

    script.run("XAUUSD")

    assert "No se pudo obtener tick de XAUUSD" in capsys.readouterr().out


def test_spread_is_calculated_from_tick(mt5_mock, capsys):
    mt5_mock.symbol_info_tick.return_value.bid = 1.10000
    mt5_mock.symbol_info_tick.return_value.ask = 1.10025

    script.run()

    assert "Spread: 0.00025" in capsys.readouterr().out


def test_shutdown_called_on_success(mt5_mock):
    script.run()
    mt5_mock.shutdown.assert_called_once()


def test_shutdown_called_even_if_terminal_info_raises(mt5_mock):
    mt5_mock.terminal_info.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError):
        script.run()

    mt5_mock.shutdown.assert_called_once()
