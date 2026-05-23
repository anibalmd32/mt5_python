# Laboratorio MetaTrader 5 + Python

Colección progresiva de scripts para explorar, analizar y automatizar trading sobre MetaTrader 5 desde Python, pensada para personas que **no necesitan saber de trading** para empezar a usarla. Cada script vive en `src/labs/nivel_X/` como un módulo independiente con una función `run()`, y se orquesta desde [main.py](main.py).

## Estructura

```
src/labs/
├── nivel_1_familiarizacion/   ← solo lectura, sin riesgo
├── nivel_2_datos/             ← descarga y visualización de histórico
├── nivel_3_analisis/          ← indicadores y escaneo
├── nivel_4_senales/           ← señales y backtesting
├── nivel_5_riesgo/            ← gestión y cálculos
└── nivel_6_ejecucion/         ← bots y dashboards (toca la cuenta)
```

Dentro de cada nivel los ficheros se prefijan con `s1_`, `s2_`, `s3_`, `s4_` siguiendo el orden del índice.

## Requisitos

- Windows + MetaTrader 5 instalado y logueado (cuenta demo o real).
- "Trading algorítmico" activado en MT5.
- Python 64-bit con entorno virtual.
- `pip install -r requirements.txt`.

---

## Índice de scripts

Ordenados de más sencillo a más complejo. Los marcados con ✓ ya están implementados.

### Nivel 1 — Familiarización (solo lectura, sin riesgo)

1. **[✓] `s1_connection_check`** — Verifica la conexión con el terminal y muestra cuenta, versión y un tick de ejemplo.
2. **[✓] `s2_symbols_explorer`** — Lista todos los instrumentos disponibles agrupados por categoría, con spread, decimales y visibilidad.
3. **`s3_account_snapshot`** — Foto fija del estado actual de la cuenta: balance, equity, posiciones abiertas, órdenes pendientes y P/L, en formato legible.
4. **`s4_market_clock`** — Indica qué sesiones del mercado mundial están abiertas (Sídney, Tokio, Londres, Nueva York) y qué pares suelen ser más activos en cada una.

### Nivel 2 — Datos históricos y visualización

5. **`history_downloader`** — Descarga velas históricas (M1, M5, H1, D1…) de un símbolo a CSV/Parquet para análisis offline.
6. **`tick_downloader`** — Igual pero a nivel tick (operación a operación), útil para microestructura.
7. **`chart_viewer`** — Dibuja un gráfico de velas con indicadores básicos usando matplotlib/plotly.
8. **`performance_comparator`** — Compara el rendimiento porcentual de varios instrumentos en el mismo periodo (¿quién subió más este mes?).

### Nivel 3 — Análisis e indicadores

9. **`volatility_report`** — Calcula la volatilidad reciente de un símbolo (ATR, rango diario medio) y lo traduce a "cuánto se mueve normalmente en pips/€".
10. **`trend_detector`** — Clasifica el mercado actual en "tendencia alcista / bajista / lateral" con medias móviles y ADX.
11. **`multi_symbol_scanner`** — Recorre muchos símbolos y los rankea por un criterio (volatilidad, momentum, ruptura), tipo "top 10 instrumentos más interesantes hoy".
12. **`correlation_matrix`** — Matriz de correlación entre pares para detectar instrumentos que se mueven igual (y evitar duplicar riesgo).

### Nivel 4 — Señales y backtesting

13. **`signal_generator`** — Genera señales sencillas (cruce de medias, RSI sobrecompra/sobreventa) y las imprime con explicación en lenguaje natural.
14. **`signal_journal`** — Registra a lo largo del tiempo todas las señales que habrían aparecido, sin operar, para evaluar su calidad.
15. **`basic_backtest`** — Simula una estrategia sobre datos históricos y devuelve métricas (ganancia total, win rate, drawdown, profit factor).
16. **`param_optimizer`** — Prueba combinaciones de parámetros del backtest y muestra cuáles funcionaron mejor (con aviso sobre el riesgo de sobreajuste).

### Nivel 5 — Gestión y riesgo

17. **`position_size_calculator`** — Dado un % de riesgo y la distancia al stop loss, calcula el tamaño exacto de la operación.
18. **`risk_monitor`** — Vigila en tiempo real exposición total, drawdown del día y uso de margen; alerta si supera umbrales.
19. **`stop_manager`** — Mueve stops automáticamente: trailing stop, break-even, partial close.
20. **`trade_journal`** — Exporta el historial de operaciones con métricas legibles (mejor día, peor hora, símbolo más rentable).

### Nivel 6 — Ejecución automatizada

21. **`single_bot`** — Bot mínimo: lee una señal de Nivel 4 y abre/cierra operaciones con SL/TP, integrado con `position_size_calculator` y `risk_monitor`.
22. **`multi_bot_orchestrator`** — Corre varias estrategias en paralelo sobre distintos símbolos, repartiendo capital.
23. **`alerts`** — Envía notificaciones a Telegram/email cuando ocurren eventos (señal, ejecución, drawdown, desconexión).
24. **`live_dashboard`** — Panel web (Streamlit) en tiempo real: equity, posiciones, señales pendientes, métricas del día.

---

## Cómo se usa

```powershell
.\.venv\Scripts\Activate.ps1
python .\main.py
```

`main.py` decide qué script lanzar. Iremos editándolo según el experimento del día.

## Filosofía del laboratorio

- **Cada script es autónomo** y se puede ejecutar suelto.
- **Cada script explica lo que hace** en su salida, no asume jerga de trading.
- **Nada toca dinero real** hasta el Nivel 6, y aun así primero en demo.
- **Iteración por capas**: no se sube al siguiente nivel sin entender el anterior.
