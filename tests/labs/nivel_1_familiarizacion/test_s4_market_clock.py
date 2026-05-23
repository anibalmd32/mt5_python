from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.labs.nivel_1_familiarizacion import s4_market_clock as script


UTC = ZoneInfo("UTC")


def _session(name: str):
    return next(s for s in script.SESSIONS if s.name == name)


# --- _format_delta ---

def test_format_delta_hours_and_minutes():
    assert script._format_delta(timedelta(hours=2, minutes=30)) == "2h 30m"


def test_format_delta_minutes_only():
    assert script._format_delta(timedelta(minutes=45)) == "45m"


def test_format_delta_exact_hour():
    assert script._format_delta(timedelta(hours=1)) == "1h 0m"


def test_format_delta_negative_is_zero():
    assert script._format_delta(timedelta(hours=-1)) == "0m"


# --- _format_es_datetime ---

def test_format_es_datetime_monday():
    assert script._format_es_datetime(datetime(2026, 5, 25, 7, 0)) == "lun 25/05 07:00"


def test_format_es_datetime_friday():
    assert script._format_es_datetime(datetime(2026, 5, 22, 22, 0)) == "vie 22/05 22:00"


# --- _is_open per session ---

def test_london_open_wednesday_afternoon():
    # Mié 12:00 UTC = mié 13:00 BST → dentro de [08:00, 17:00)
    assert script._is_open(_session("Londres"), datetime(2026, 5, 20, 12, 0, tzinfo=UTC)) is True


def test_london_closed_saturday_even_during_hours():
    # Sáb 12:00 UTC = sáb 13:00 BST → la hora es de apertura, pero es fin de semana
    assert script._is_open(_session("Londres"), datetime(2026, 5, 23, 12, 0, tzinfo=UTC)) is False


def test_london_closed_outside_hours():
    # Mié 23:00 UTC = jue 00:00 BST → 00 no está en [08, 17)
    assert script._is_open(_session("Londres"), datetime(2026, 5, 20, 23, 0, tzinfo=UTC)) is False


def test_sydney_open_when_london_closed():
    # Mar 03:00 UTC = mar 13:00 AEST → Sídney abierto, Londres aún cerrado
    when = datetime(2026, 5, 19, 3, 0, tzinfo=UTC)
    assert script._is_open(_session("Sídney"), when) is True
    assert script._is_open(_session("Londres"), when) is False


def test_new_york_open_during_overlap_with_london():
    # Mié 14:00 UTC = NY 10:00 EDT y Londres 15:00 BST → ambos abiertos
    when = datetime(2026, 5, 20, 14, 0, tzinfo=UTC)
    assert script._is_open(_session("Londres"), when) is True
    assert script._is_open(_session("Nueva York"), when) is True


# --- _next_open ---

def test_next_open_skips_weekend():
    # Vie 22:00 UTC = sáb 00:00 BST en Londres → próxima apertura lun 08:00 BST
    nxt = script._next_open(_session("Londres"), datetime(2026, 5, 22, 22, 0, tzinfo=UTC))
    assert nxt.weekday() == 0  # lunes
    assert nxt.hour == 8


def test_next_open_today_if_before_open():
    # Mié 04:00 UTC = mié 05:00 BST (antes de 8am) → abre hoy mismo a las 08:00 BST
    nxt = script._next_open(_session("Londres"), datetime(2026, 5, 20, 4, 0, tzinfo=UTC))
    assert nxt.weekday() == 2  # miércoles
    assert nxt.hour == 8


def test_next_open_tomorrow_if_after_close():
    # Mié 20:00 UTC = mié 21:00 BST (post cierre) → abre jue 08:00 BST
    nxt = script._next_open(_session("Londres"), datetime(2026, 5, 20, 20, 0, tzinfo=UTC))
    assert nxt.weekday() == 3  # jueves
    assert nxt.hour == 8


# --- _time_to_close ---

def test_time_to_close_in_middle_of_session():
    # Mié 12:00 UTC = mié 13:00 BST, cierre a 17:00 BST → 4h restantes
    ttc = script._time_to_close(_session("Londres"), datetime(2026, 5, 20, 12, 0, tzinfo=UTC))
    assert ttc == timedelta(hours=4)


# --- run() integración ---

def test_run_prints_header(capsys):
    script.run(datetime(2026, 5, 23, 12, 0, tzinfo=UTC))
    out = capsys.readouterr().out
    assert "=== Reloj de mercado ===" in out
    assert "UTC:" in out
    assert "Tu hora:" in out


def test_run_forex_closed_on_saturday(capsys):
    script.run(datetime(2026, 5, 23, 12, 0, tzinfo=UTC))
    out = capsys.readouterr().out
    assert "Forex: CERRADO" in out
    assert "Próxima apertura: Sídney" in out


def test_run_forex_open_during_london_ny_overlap(capsys):
    script.run(datetime(2026, 5, 20, 14, 0, tzinfo=UTC))
    out = capsys.readouterr().out
    assert "Forex: ABIERTO" in out
    assert "Londres" in out
    assert "Nueva York" in out


def test_run_lists_all_four_sessions(capsys):
    script.run(datetime(2026, 5, 23, 12, 0, tzinfo=UTC))
    out = capsys.readouterr().out
    assert "Sídney" in out
    assert "Tokio" in out
    assert "Londres" in out
    assert "Nueva York" in out


def test_run_lists_active_instruments(capsys):
    script.run(datetime(2026, 5, 23, 12, 0, tzinfo=UTC))
    out = capsys.readouterr().out
    assert "EUR/USD" in out
    assert "AUD/USD" in out
    assert "USD/JPY" in out


def test_run_with_naive_datetime_treats_as_utc(capsys):
    script.run(datetime(2026, 5, 23, 12, 0))  # sin tzinfo
    out = capsys.readouterr().out
    assert "Forex: CERRADO" in out


def test_run_without_args_does_not_crash(capsys):
    script.run()
    assert "Reloj de mercado" in capsys.readouterr().out


def test_friday_after_ny_close_forex_closed(capsys):
    # Vie 22:00 UTC = vie 18:00 EDT (NY cerró a las 17) → forex cerrado
    script.run(datetime(2026, 5, 22, 22, 0, tzinfo=UTC))
    assert "Forex: CERRADO" in capsys.readouterr().out


def test_sunday_evening_sydney_opens_forex(capsys):
    # Dom 22:00 UTC = lun 08:00 AEST → Sídney abre, forex abre
    script.run(datetime(2026, 5, 24, 22, 0, tzinfo=UTC))
    out = capsys.readouterr().out
    assert "Forex: ABIERTO" in out
    assert "Sídney" in out
