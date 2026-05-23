from src.labs.nivel_2_datos import s5_history_downloader


if __name__ == "__main__":
    s5_history_downloader.run(symbol="USDJPY", timeframe="H1", count=500)
