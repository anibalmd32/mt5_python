import pytest

from src import connection_check


def test_initialize_failure_prints_error_and_returns(mocker, capsys):
    mt5 = mocker.patch("src.connection_check.mt5")
    mt5.initialize.return_value = False
    mt5.last_error.return_value = (-10003, "IPC timeout")

    connection_check.run()

    out = capsys.readouterr().out
    assert "initialize() falló" in out
    assert "-10003" in out
    mt5.terminal_info.assert_not_called()
    mt5.shutdown.assert_not_called()


def test_successful_run_prints_all_sections(mt5_mock, capsys):
    connection_check.run()

    out = capsys.readouterr().out
    assert "=== Terminal ===" in out
    assert "=== Cuenta ===" in out
    assert "=== Último tick EURUSD ===" in out


def test_successful_run_includes_account_details(mt5_mock, capsys):
    connection_check.run()

    out = capsys.readouterr().out
    assert "107401078" in out
    assert "MetaQuotes-Demo" in out
    assert "USD" in out
    assert "100000.0" in out
    assert "1:100" in out


def test_hedge_account_label(mt5_mock, capsys):
    connection_check.run()

    out = capsys.readouterr().out
    assert "Tipo cuenta:  Hedge" in out


def test_netting_account_label(mt5_mock, capsys):
    mt5_mock.account_info.return_value.margin_mode = 0

    connection_check.run()

    out = capsys.readouterr().out
    assert "Tipo cuenta:  Otro" in out


def test_custom_symbol_is_requested(mt5_mock, capsys):
    connection_check.run("USDJPY")

    out = capsys.readouterr().out
    mt5_mock.symbol_info_tick.assert_called_once_with("USDJPY")
    assert "=== Último tick USDJPY ===" in out


def test_tick_none_prints_warning(mt5_mock, capsys):
    mt5_mock.symbol_info_tick.return_value = None

    connection_check.run("XAUUSD")

    out = capsys.readouterr().out
    assert "No se pudo obtener tick de XAUUSD" in out


def test_spread_is_calculated_from_tick(mt5_mock, capsys):
    mt5_mock.symbol_info_tick.return_value.bid = 1.10000
    mt5_mock.symbol_info_tick.return_value.ask = 1.10025

    connection_check.run()

    out = capsys.readouterr().out
    assert "Spread: 0.00025" in out


def test_shutdown_called_on_success(mt5_mock):
    connection_check.run()
    mt5_mock.shutdown.assert_called_once()


def test_shutdown_called_even_if_terminal_info_raises(mt5_mock):
    mt5_mock.terminal_info.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError):
        connection_check.run()

    mt5_mock.shutdown.assert_called_once()
