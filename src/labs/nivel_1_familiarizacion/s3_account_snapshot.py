"""Foto fija del estado actual de la cuenta MT5.

Muestra tres bloques pensados para un usuario no técnico:

1. Resumen financiero (balance, equity, P/L flotante, margen).
2. Posiciones abiertas (lo que tienes en marcha ahora mismo).
3. Órdenes pendientes (lo que has dejado preparado para activarse en un precio).

No modifica nada: es 100% solo lectura.
"""

import MetaTrader5 as mt5


POSITION_TYPE_NAMES = {
    0: "COMPRA",  # mt5.POSITION_TYPE_BUY
    1: "VENTA",   # mt5.POSITION_TYPE_SELL
}

ORDER_TYPE_NAMES = {
    0: "COMPRA mercado",
    1: "VENTA mercado",
    2: "COMPRA límite",
    3: "VENTA límite",
    4: "COMPRA stop",
    5: "VENTA stop",
    6: "COMPRA stop-límite",
    7: "VENTA stop-límite",
}


def _print_account_summary(account) -> None:
    currency = account.currency
    margin_level = (
        f"{account.margin_level:.2f} %"
        if account.margin > 0
        else "N/A (sin posiciones)"
    )

    print("=== Resumen de cuenta ===")
    print(f"  Login:          {account.login}")
    print(f"  Servidor:       {account.server}")
    print(f"  Moneda:         {currency}")
    print()
    print(f"  Balance:        {account.balance:>12,.2f} {currency}   (dinero ya realizado/depositado)")
    print(f"  Equity:         {account.equity:>12,.2f} {currency}   (balance + P/L flotante)")
    print(f"  P/L flotante:   {account.profit:>+12,.2f} {currency}   (lo que ganarías/perderías si cerraras todo ahora)")
    print()
    print(f"  Margen usado:   {account.margin:>12,.2f} {currency}")
    print(f"  Margen libre:   {account.margin_free:>12,.2f} {currency}")
    print(f"  Nivel margen:   {margin_level}")


def _print_positions(positions, currency: str) -> None:
    print("\n=== Posiciones abiertas ===")
    if not positions:
        print("  No hay posiciones abiertas.")
        return

    print(f"  Total: {len(positions)}")
    total_pl = 0.0
    for p in positions:
        tipo = POSITION_TYPE_NAMES.get(p.type, str(p.type))
        sl = f"{p.sl:.5f}" if p.sl else "-"
        tp = f"{p.tp:.5f}" if p.tp else "-"
        print(
            f"  #{p.ticket}  {p.symbol:<8} {tipo:<6}  "
            f"vol={p.volume:.2f}  entrada={p.price_open:.5f}  actual={p.price_current:.5f}  "
            f"SL={sl}  TP={tp}  P/L={p.profit:+.2f} {currency}"
        )
        total_pl += p.profit
    print(f"  Total P/L abierto: {total_pl:+.2f} {currency}")


def _print_orders(orders) -> None:
    print("\n=== Órdenes pendientes ===")
    if not orders:
        print("  No hay órdenes pendientes.")
        return

    print(f"  Total: {len(orders)}")
    for o in orders:
        tipo = ORDER_TYPE_NAMES.get(o.type, str(o.type))
        sl = f"{o.sl:.5f}" if o.sl else "-"
        tp = f"{o.tp:.5f}" if o.tp else "-"
        print(
            f"  #{o.ticket}  {o.symbol:<8} {tipo:<18}  "
            f"vol={o.volume_initial:.2f}  precio={o.price_open:.5f}  "
            f"SL={sl}  TP={tp}"
        )


def run() -> None:
    """Imprime un snapshot completo: cuenta + posiciones + órdenes."""
    if not mt5.initialize():
        print(f"initialize() falló. Código: {mt5.last_error()}")
        return

    try:
        account = mt5.account_info()
        if account is None:
            print("No se pudo obtener información de la cuenta.")
            return

        positions = mt5.positions_get() or ()
        orders = mt5.orders_get() or ()

        _print_account_summary(account)
        _print_positions(positions, account.currency)
        _print_orders(orders)
    finally:
        mt5.shutdown()
