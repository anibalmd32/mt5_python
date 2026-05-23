import pytest

from src.labs.nivel_1_familiarizacion import s3_account_snapshot as script
from tests.helpers import (
    build_account_mock,
    build_order_mock,
    build_position_mock,
)


MT5_PATH = "src.labs.nivel_1_familiarizacion.s3_account_snapshot.mt5"


@pytest.fixture
def mt5_mock(mocker):
    mt5 = mocker.patch(MT5_PATH)
    mt5.initialize.return_value = True
    mt5.last_error.return_value = (0, "ok")
    mt5.account_info.return_value = build_account_mock()
    mt5.positions_get.return_value = ()
    mt5.orders_get.return_value = ()
    return mt5


def test_initialize_failure_returns_silently(mocker, capsys):
    mt5 = mocker.patch(MT5_PATH)
    mt5.initialize.return_value = False
    mt5.last_error.return_value = (-1, "x")

    script.run()

    out = capsys.readouterr().out
    assert "initialize() falló" in out
    mt5.account_info.assert_not_called()
    mt5.shutdown.assert_not_called()


def test_account_info_none_warns(mt5_mock, capsys):
    mt5_mock.account_info.return_value = None

    script.run()

    assert "No se pudo obtener información" in capsys.readouterr().out


def test_summary_shows_account_basics(mt5_mock, capsys):
    script.run()

    out = capsys.readouterr().out
    assert "107401078" in out
    assert "MetaQuotes-Demo" in out
    assert "USD" in out
    assert "100,000.00" in out


def test_floating_pl_shown(mt5_mock, capsys):
    mt5_mock.account_info.return_value.profit = 150.5

    script.run()

    assert "+150.50" in capsys.readouterr().out


def test_margin_level_na_when_no_margin(mt5_mock, capsys):
    script.run()

    assert "N/A (sin posiciones)" in capsys.readouterr().out


def test_margin_level_shown_when_margin_used(mt5_mock, capsys):
    mt5_mock.account_info.return_value.margin = 1000.0
    mt5_mock.account_info.return_value.margin_level = 9500.50

    script.run()

    assert "9500.50 %" in capsys.readouterr().out


def test_no_positions_message(mt5_mock, capsys):
    script.run()

    assert "No hay posiciones abiertas." in capsys.readouterr().out


def test_no_orders_message(mt5_mock, capsys):
    script.run()

    assert "No hay órdenes pendientes." in capsys.readouterr().out


def test_position_buy_displayed(mt5_mock, capsys):
    mt5_mock.positions_get.return_value = (
        build_position_mock(
            ticket=1001, symbol="EURUSD", ptype=0, volume=0.10,
            price_open=1.10000, price_current=1.10050, profit=5.0,
        ),
    )

    script.run()

    out = capsys.readouterr().out
    assert "#1001" in out
    assert "EURUSD" in out
    assert "COMPRA" in out
    assert "+5.00" in out


def test_position_sell_displayed(mt5_mock, capsys):
    mt5_mock.positions_get.return_value = (
        build_position_mock(ticket=1002, symbol="USDJPY", ptype=1, profit=-12.5),
    )

    script.run()

    out = capsys.readouterr().out
    assert "VENTA" in out
    assert "-12.50" in out


def test_position_sl_tp_dash_when_zero(mt5_mock, capsys):
    mt5_mock.positions_get.return_value = (
        build_position_mock(sl=0.0, tp=0.0),
    )

    script.run()

    out = capsys.readouterr().out
    assert "SL=-" in out
    assert "TP=-" in out


def test_position_sl_tp_formatted_when_set(mt5_mock, capsys):
    mt5_mock.positions_get.return_value = (
        build_position_mock(sl=1.09500, tp=1.10500),
    )

    script.run()

    out = capsys.readouterr().out
    assert "SL=1.09500" in out
    assert "TP=1.10500" in out


def test_position_total_pl(mt5_mock, capsys):
    mt5_mock.positions_get.return_value = (
        build_position_mock(profit=10.0),
        build_position_mock(profit=-3.0),
        build_position_mock(profit=2.5),
    )

    script.run()

    assert "Total P/L abierto: +9.50" in capsys.readouterr().out


def test_pending_order_displayed(mt5_mock, capsys):
    mt5_mock.orders_get.return_value = (
        build_order_mock(
            ticket=2001, symbol="GBPUSD", otype=2, volume=0.50,
            price_open=1.30000, sl=1.29500, tp=1.31000,
        ),
    )

    script.run()

    out = capsys.readouterr().out
    assert "#2001" in out
    assert "GBPUSD" in out
    assert "COMPRA límite" in out
    assert "vol=0.50" in out
    assert "precio=1.30000" in out


def test_order_type_names(mt5_mock, capsys):
    mt5_mock.orders_get.return_value = (
        build_order_mock(otype=2),  # buy limit
        build_order_mock(otype=3),  # sell limit
        build_order_mock(otype=4),  # buy stop
        build_order_mock(otype=5),  # sell stop
    )

    script.run()

    out = capsys.readouterr().out
    assert "COMPRA límite" in out
    assert "VENTA límite" in out
    assert "COMPRA stop" in out
    assert "VENTA stop" in out


def test_positions_get_none_treated_as_empty(mt5_mock, capsys):
    mt5_mock.positions_get.return_value = None

    script.run()

    assert "No hay posiciones abiertas." in capsys.readouterr().out


def test_orders_get_none_treated_as_empty(mt5_mock, capsys):
    mt5_mock.orders_get.return_value = None

    script.run()

    assert "No hay órdenes pendientes." in capsys.readouterr().out


def test_shutdown_called_on_success(mt5_mock):
    script.run()
    mt5_mock.shutdown.assert_called_once()


def test_shutdown_called_on_exception(mt5_mock):
    mt5_mock.positions_get.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError):
        script.run()

    mt5_mock.shutdown.assert_called_once()
