import MetaTrader5 as mt5


def run(symbol: str = "EURUSD") -> None:
    if not mt5.initialize():
        print(f"initialize() falló. Código de error: {mt5.last_error()}")
        return

    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()

        print("=== Terminal ===")
        print(f"Nombre:       {terminal.name}")
        print(f"Conectado:    {terminal.connected}")
        print(f"Ruta:         {terminal.path}")
        print(f"Versión MT5:  {mt5.version()}")

        print("\n=== Cuenta ===")
        print(f"Login:        {account.login}")
        print(f"Servidor:     {account.server}")
        print(f"Moneda:       {account.currency}")
        print(f"Balance:      {account.balance}")
        print(f"Equity:       {account.equity}")
        print(f"Apalancam.:   1:{account.leverage}")
        print(f"Tipo cuenta:  {'Hedge' if account.margin_mode == mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING else 'Otro'}")

        tick = mt5.symbol_info_tick(symbol)
        if tick is not None:
            print(f"\n=== Último tick {symbol} ===")
            print(f"Bid: {tick.bid}  Ask: {tick.ask}  Spread: {round(tick.ask - tick.bid, 5)}")
        else:
            print(f"\nNo se pudo obtener tick de {symbol} (¿está en Observación del mercado?).")

    finally:
        mt5.shutdown()
