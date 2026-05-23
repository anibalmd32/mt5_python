import pytest

from src.labs.nivel_1_familiarizacion import s2_symbols_explorer as script
from tests.helpers import build_symbol_mock


MT5_PATH = "src.labs.nivel_1_familiarizacion.s2_symbols_explorer.mt5"


@pytest.fixture
def mt5_mock(mocker):
    mt5 = mocker.patch(MT5_PATH)
    mt5.initialize.return_value = True
    mt5.last_error.return_value = (0, "No error")
    mt5.symbols_get.return_value = [
        build_symbol_mock("EURUSD", "Forex\\Majors\\EURUSD", spread=1),
        build_symbol_mock("GBPUSD", "Forex\\Majors\\GBPUSD", spread=2),
        build_symbol_mock("BTCUSD", "Crypto\\BTCUSD", spread=50, digits=2),
        build_symbol_mock("US500", "Indices\\US500", spread=3, digits=1),
    ]
    return mt5


def test_initialize_failure_prints_error(mocker, capsys):
    mt5 = mocker.patch(MT5_PATH)
    mt5.initialize.return_value = False
    mt5.last_error.return_value = (-1, "fail")

    script.run()

    out = capsys.readouterr().out
    assert "initialize() falló" in out
    mt5.symbols_get.assert_not_called()
    mt5.shutdown.assert_not_called()


def test_summary_shows_total_and_categories(mt5_mock, capsys):
    script.run()

    out = capsys.readouterr().out
    assert "Total de símbolos: 4" in out
    assert "Forex" in out
    assert "Crypto" in out
    assert "Indices" in out


def test_categories_count_correctly(mt5_mock, capsys):
    script.run()

    out = capsys.readouterr().out
    assert "Forex" in out
    forex_line = next(line for line in out.splitlines() if line.strip().startswith("Forex"))
    assert "2" in forex_line


def test_listing_orders_by_category_then_spread(mt5_mock, capsys):
    script.run()

    out = capsys.readouterr().out
    assert out.index("EURUSD") < out.index("GBPUSD")
    assert out.index("BTCUSD") < out.index("EURUSD")


def test_filter_pattern_is_forwarded(mt5_mock):
    script.run(filter_pattern="*USD*")
    mt5_mock.symbols_get.assert_called_once_with("*USD*")


def test_no_filter_calls_symbols_get_with_no_args(mt5_mock):
    script.run()
    mt5_mock.symbols_get.assert_called_once_with()


def test_limit_truncates_listing_but_not_summary(mt5_mock, capsys):
    script.run(limit=2)

    out = capsys.readouterr().out
    assert "Total de símbolos: 4" in out
    assert "Listado (2 de 4" in out


def test_empty_result_prints_warning(mt5_mock, capsys):
    mt5_mock.symbols_get.return_value = []

    script.run()

    assert "No se obtuvieron símbolos" in capsys.readouterr().out


def test_none_result_treated_as_empty(mt5_mock, capsys):
    mt5_mock.symbols_get.return_value = None

    script.run()

    assert "No se obtuvieron símbolos" in capsys.readouterr().out


def test_symbol_without_path_falls_in_otros(mt5_mock, capsys):
    mt5_mock.symbols_get.return_value = [build_symbol_mock("WEIRD", "")]

    script.run()

    assert "Otros" in capsys.readouterr().out


def test_filter_in_header_when_provided(mt5_mock, capsys):
    script.run(filter_pattern="*USD*")
    assert "filtro: *USD*" in capsys.readouterr().out


def test_shutdown_called_on_success(mt5_mock):
    script.run()
    mt5_mock.shutdown.assert_called_once()


def test_shutdown_called_on_exception(mt5_mock):
    mt5_mock.symbols_get.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError):
        script.run()

    mt5_mock.shutdown.assert_called_once()
