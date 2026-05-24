from src.labs.nivel_2_datos import s6_tick_downloader


if __name__ == "__main__":
    s6_tick_downloader.run(symbol="USDJPY", hours_back=74.0, flags="all")
