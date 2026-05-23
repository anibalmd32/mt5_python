"""Reloj de mercado: dice qué sesiones forex están abiertas y cuántas horas
faltan para la próxima apertura.

NO requiere MT5 abierto. Es pura lógica de zonas horarias: las cuatro sesiones
forex tradicionales (Sídney, Tokio, Londres, Nueva York) son una convención
universal, no algo específico de tu broker.

Útil para responder de un vistazo:
- ¿Está el mercado activo ahora mismo?
- Si no, ¿cuánto falta para que abra?
- ¿Qué pares se mueven más en esta hora del día?
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


UTC = ZoneInfo("UTC")

DAY_NAMES_ES = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


@dataclass(frozen=True)
class Session:
    """Una sesión de mercado definida por su ciudad y horario local."""
    name: str
    tz: str               # nombre IANA, ej. "Europe/London"
    open_hour: int        # hora local de apertura (0-23)
    close_hour: int       # hora local de cierre (0-23)
    instruments: tuple[str, ...]


SESSIONS: tuple[Session, ...] = (
    Session("Sídney",     "Australia/Sydney", 7, 16, ("AUD/USD", "NZD/USD", "AUD/JPY")),
    Session("Tokio",      "Asia/Tokyo",       9, 18, ("USD/JPY", "EUR/JPY", "AUD/JPY")),
    Session("Londres",    "Europe/London",    8, 17, ("EUR/USD", "GBP/USD", "EUR/GBP")),
    Session("Nueva York", "America/New_York", 8, 17, ("EUR/USD", "USD/CAD", "USD/JPY")),
)


def _is_open(session: Session, now_utc: datetime) -> bool:
    """¿Está abierta la sesión en este instante?"""
    local = now_utc.astimezone(ZoneInfo(session.tz))
    if local.weekday() >= 5:  # 5 = sábado, 6 = domingo
        return False
    return session.open_hour <= local.hour < session.close_hour


def _time_to_close(session: Session, now_utc: datetime) -> timedelta:
    """Tiempo restante hasta el cierre (solo válido si la sesión está abierta)."""
    local = now_utc.astimezone(ZoneInfo(session.tz))
    close = local.replace(hour=session.close_hour, minute=0, second=0, microsecond=0)
    return close - local


def _next_open(session: Session, now_utc: datetime) -> datetime:
    """Devuelve el datetime de la próxima apertura en la TZ de la sesión.

    Salta sábados y domingos. Busca hasta 8 días por delante (suficiente para
    cubrir cualquier fin de semana largo).
    """
    local = now_utc.astimezone(ZoneInfo(session.tz))
    for offset in range(8):
        candidate = (local + timedelta(days=offset)).replace(
            hour=session.open_hour, minute=0, second=0, microsecond=0
        )
        if candidate <= local:
            continue
        if candidate.weekday() >= 5:
            continue
        return candidate
    raise RuntimeError("no se encontró próxima apertura en 8 días")


def _time_until_next_open(session: Session, now_utc: datetime) -> timedelta:
    nxt = _next_open(session, now_utc)
    local_now = now_utc.astimezone(ZoneInfo(session.tz))
    return nxt - local_now


def _format_delta(delta: timedelta) -> str:
    """Convierte un timedelta a 'Xh Ym' o 'Xm' (sin segundos)."""
    total_minutes = max(0, int(delta.total_seconds() // 60))
    hours, minutes = divmod(total_minutes, 60)
    if hours == 0:
        return f"{minutes}m"
    return f"{hours}h {minutes}m"


def _format_es_datetime(dt: datetime) -> str:
    """Formato corto en español: 'lun 25/05 07:00'."""
    day = DAY_NAMES_ES[dt.weekday()]
    return f"{day} {dt.strftime('%d/%m %H:%M')}"


def _print_header(now_utc: datetime) -> None:
    user_local = now_utc.astimezone()
    print("=== Reloj de mercado ===")
    print(f"  UTC:     {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Tu hora: {user_local.strftime('%Y-%m-%d %H:%M:%S %z')}")


def _print_global_status(now_utc: datetime) -> None:
    open_sessions = [s for s in SESSIONS if _is_open(s, now_utc)]
    if open_sessions:
        names = ", ".join(s.name for s in open_sessions)
        print(f"  Forex: ABIERTO  ({len(open_sessions)} sesion(es) activa(s): {names})")
    else:
        soonest = min(SESSIONS, key=lambda s: _time_until_next_open(s, now_utc))
        delta = _time_until_next_open(soonest, now_utc)
        nxt = _next_open(soonest, now_utc)
        print("  Forex: CERRADO")
        print(
            f"  Próxima apertura: {soonest.name} en {_format_delta(delta)} "
            f"({_format_es_datetime(nxt)} hora {soonest.name})"
        )


def _print_session(session: Session, now_utc: datetime) -> None:
    print(f"  {session.name} ({session.tz})")
    if _is_open(session, now_utc):
        ttc = _time_to_close(session, now_utc)
        local = now_utc.astimezone(ZoneInfo(session.tz))
        close_local = local.replace(
            hour=session.close_hour, minute=0, second=0, microsecond=0
        )
        print(
            f"    ABIERTA — cierra a las {close_local.strftime('%H:%M')} "
            f"({_format_delta(ttc)} restantes)"
        )
    else:
        nxt = _next_open(session, now_utc)
        delta = _time_until_next_open(session, now_utc)
        print(
            f"    Cerrada — abre {_format_es_datetime(nxt)} hora {session.name} "
            f"({_format_delta(delta)} restantes)"
        )
    print(f"    Pares más activos: {', '.join(session.instruments)}")


def run(now_utc: datetime | None = None) -> None:
    """Imprime el estado de las cuatro sesiones forex principales.

    Args:
        now_utc: instante a evaluar (datetime tz-aware en UTC). Si es None,
            usa la hora actual. Si llega naive, se asume UTC.
            Útil para simular escenarios futuros (`datetime(2026, 5, 25, 7, 0)`)
            sin esperar a que el reloj llegue ahí.
    """
    if now_utc is None:
        now_utc = datetime.now(UTC)
    elif now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=UTC)

    _print_header(now_utc)
    print()
    _print_global_status(now_utc)
    print()
    print("Sesiones individuales:")
    for s in SESSIONS:
        _print_session(s, now_utc)
        print()
