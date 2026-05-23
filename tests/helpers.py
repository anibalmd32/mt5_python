"""Builders de mocks reutilizables para los tests.

Se usan como funciones (no como fixtures) para mantener cada test desacoplado
del módulo concreto que está parcheando.
"""

from unittest.mock import MagicMock


HEDGING_MODE = 2


def build_terminal_mock() -> MagicMock:
    terminal = MagicMock()
    terminal.name = "MetaTrader 5"
    terminal.connected = True
    terminal.path = r"C:\Program Files\MetaTrader 5"
    return terminal


def build_account_mock() -> MagicMock:
    account = MagicMock()
    account.login = 107401078
    account.server = "MetaQuotes-Demo"
    account.currency = "USD"
    account.balance = 100_000.0
    account.equity = 100_000.0
    account.leverage = 100
    account.margin_mode = HEDGING_MODE
    return account


def build_tick_mock(bid: float = 1.16032, ask: float = 1.16033) -> MagicMock:
    tick = MagicMock()
    tick.bid = bid
    tick.ask = ask
    return tick


def build_symbol_mock(
    name: str,
    path: str,
    spread: int = 1,
    digits: int = 5,
    visible: bool = True,
    description: str = "",
) -> MagicMock:
    s = MagicMock()
    s.name = name
    s.path = path
    s.spread = spread
    s.digits = digits
    s.visible = visible
    s.description = description
    return s
