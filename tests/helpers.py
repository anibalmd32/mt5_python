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
    account.profit = 0.0
    account.margin = 0.0
    account.margin_free = 100_000.0
    account.margin_level = 0.0
    account.leverage = 100
    account.margin_mode = HEDGING_MODE
    return account


def build_position_mock(
    ticket: int = 1000,
    symbol: str = "EURUSD",
    ptype: int = 0,
    volume: float = 0.10,
    price_open: float = 1.10000,
    price_current: float = 1.10000,
    sl: float = 0.0,
    tp: float = 0.0,
    profit: float = 0.0,
    swap: float = 0.0,
) -> MagicMock:
    p = MagicMock()
    p.ticket = ticket
    p.symbol = symbol
    p.type = ptype
    p.volume = volume
    p.price_open = price_open
    p.price_current = price_current
    p.sl = sl
    p.tp = tp
    p.profit = profit
    p.swap = swap
    return p


def build_rates_array(n: int = 5):
    """Estructura idéntica a la que devuelve mt5.copy_rates_from_pos.

    Es un numpy structured array con dtype fijo (time int64, OHLC float64,
    volúmenes y spread enteros). pandas.DataFrame lo lee directamente.
    """
    import numpy as np

    dtype = np.dtype([
        ("time", "i8"),
        ("open", "f8"),
        ("high", "f8"),
        ("low", "f8"),
        ("close", "f8"),
        ("tick_volume", "i8"),
        ("spread", "i4"),
        ("real_volume", "i8"),
    ])
    rows = [
        (
            1_700_000_000 + i * 3600,
            1.10000 + i * 0.0001,
            1.10100 + i * 0.0001,
            1.09900 + i * 0.0001,
            1.10050 + i * 0.0001,
            100 + i,
            1,
            0,
        )
        for i in range(n)
    ]
    return np.array(rows, dtype=dtype)


def build_order_mock(
    ticket: int = 2000,
    symbol: str = "EURUSD",
    otype: int = 2,
    volume: float = 0.10,
    price_open: float = 1.10000,
    sl: float = 0.0,
    tp: float = 0.0,
) -> MagicMock:
    o = MagicMock()
    o.ticket = ticket
    o.symbol = symbol
    o.type = otype
    o.volume_initial = volume
    o.price_open = price_open
    o.sl = sl
    o.tp = tp
    return o


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
