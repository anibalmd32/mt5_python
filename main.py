from src.labs.nivel_2_datos import s8_performance_comparator


if __name__ == "__main__":
    s8_performance_comparator.run(
        symbols=("EURUSD", "GBPUSD", "USDJPY", "AUDUSD"),
        timeframe="D1",
        count=30,
    )
