"""Fixtures compartidos por todos los tests.

Mockean por completo el módulo MetaTrader5 para que los tests:
- No requieran un terminal MT5 abierto.
- No dependan de datos reales del broker.
- Sean reproducibles y rápidos.
"""

from unittest.mock import MagicMock

import pytest


HEDGING_MODE = 2


def _build_terminal_mock() -> MagicMock:
    terminal = MagicMock()
    terminal.name = "MetaTrader 5"
    terminal.connected = True
    terminal.path = r"C:\Program Files\MetaTrader 5"
    return terminal


def _build_account_mock() -> MagicMock:
    account = MagicMock()
    account.login = 107401078
    account.server = "MetaQuotes-Demo"
    account.currency = "USD"
    account.balance = 100_000.0
    account.equity = 100_000.0
    account.leverage = 100
    account.margin_mode = HEDGING_MODE
    return account


def _build_tick_mock() -> MagicMock:
    tick = MagicMock()
    tick.bid = 1.16032
    tick.ask = 1.16033
    return tick


@pytest.fixture
def mt5_mock(mocker):
    """Reemplaza `mt5` dentro de `src.connection_check` con un mock funcional."""
    mt5 = mocker.patch("src.connection_check.mt5")

    mt5.initialize.return_value = True
    mt5.last_error.return_value = (0, "No error")
    mt5.terminal_info.return_value = _build_terminal_mock()
    mt5.account_info.return_value = _build_account_mock()
    mt5.version.return_value = (500, 5836, "28 Apr 2026")
    mt5.symbol_info_tick.return_value = _build_tick_mock()
    mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING = HEDGING_MODE

    return mt5
