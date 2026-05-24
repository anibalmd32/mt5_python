from src.labs.nivel_2_datos import s7_chart_viewer


if __name__ == "__main__":
    s7_chart_viewer.run(
        symbol="USDJPY",
        timeframe="H1",
        count=300,
        indicators=("SMA20", "SMA50"),
    )
