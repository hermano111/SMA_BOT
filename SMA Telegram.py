import yfinance as yf
import talib
import numpy as np
import matplotlib.pyplot as plt
import requests
import pandas as pd
import schedule
import time
from datetime import datetime
import pytz


# Función para enviar un mensaje a un canal de Telegram
def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {"chat_id": chat_id, "text": message}
    response = requests.get(url, params=params)
    return response


# Función para enviar un gráfico a un canal de Telegram
def send_telegram_photo(token, chat_id, photo_path):
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        params = {"chat_id": chat_id}
        files = {"photo": photo}
        response = requests.post(url, params=params, files=files)
    return response


# Función para descargar los datos de yfinance y calcular las medias móviles
def get_stock_data(ticker, period_fast, period_slow):
    # Definir el periodo de tiempo para obtener los datos (máximo entre period_fast y period_slow)
    days = max(period_fast, period_slow)

    # Descargar datos históricos (desde hoy hasta los días necesarios para calcular las medias)
    df = yf.download(ticker, period='3mo')  # 10 días extra por seguridad

    # Calcular medias móviles
    df['SMA_fast'] = talib.SMA(df['Close'], timeperiod=period_fast)
    df['SMA_slow'] = talib.SMA(df['Close'], timeperiod=period_slow)

    return df


# Función para detectar cruces de medias móviles
def check_crossovers(df):
    signals = []
    positions = []

    for i in range(1, len(df)):
        sma_fast_yesterday = df['SMA_fast'].iloc[i - 1]
        sma_slow_yesterday = df['SMA_slow'].iloc[i - 1]
        sma_fast_today = df['SMA_fast'].iloc[i]
        sma_slow_today = df['SMA_slow'].iloc[i]

        # Cruce alcista (señal de compra)
        if sma_fast_yesterday < sma_slow_yesterday and sma_fast_today > sma_slow_today:
            signals.append((df.index[i], 'buy', df['Close'].iloc[i]))
            positions.append(df['Close'].iloc[i])

        # Cruce bajista (señal de venta)
        elif sma_fast_yesterday > sma_slow_yesterday and sma_fast_today < sma_slow_today and len(positions) > 0:
            buy_price = positions.pop(0)  # Asumimos que vendemos la primera posición de compra
            sell_price = df['Close'].iloc[i]
            profit = (sell_price - buy_price) / buy_price * 100
            signals.append((df.index[i], 'sell', df['Close'].iloc[i], profit))

    return signals


# Función para generar gráfico de rendimiento histórico
def plot_cumulative_returns(df, signals, output_path):
    # Crear una columna de posición de compra/venta
    df['Position'] = np.nan
    for signal in signals:
        date, action, price = signal[:3]
        df.loc[date, 'Position'] = 1 if action == 'buy' else 0

    df['Position'].fillna(method='ffill', inplace=True)

    # Calcular el rendimiento diario
    df['Daily_Return'] = df['Close'].pct_change()

    # Calcular el rendimiento acumulado (con posiciones)
    df['Strategy_Return'] = df['Position'].shift(1) * df['Daily_Return']
    df['Cumulative_Strategy_Return'] = (1 + df['Strategy_Return']).cumprod()

    # Generar gráfico
    plt.figure(figsize=(10, 6))
    plt.plot(df.index, df['Cumulative_Strategy_Return'], label='Estrategia')
    plt.title('Rendimiento Acumulado de la Estrategia')
    plt.xlabel('Fecha')
    plt.ylabel('Rendimiento acumulado')
    plt.legend()
    plt.grid(True)

    plt.savefig(output_path)
    plt.close()


# Función principal del bot
def trading_bot(ticker, period_fast, period_slow, telegram_token, chat_id):
    # Obtener los datos del activo
    df = get_stock_data(ticker, period_fast, period_slow)

    # Verificar cruces de medias móviles
    signals = check_crossovers(df)

    # Enviar señales de compra/venta a Telegram
    for signal in signals:
        date, action, price = signal[:3]
        if action == 'buy':
            message = f"Señal de COMPRA detectada en {ticker} en {date.strftime('%Y-%m-%d')}. Precio: ${price:.2f}."
            send_telegram_message(telegram_token, chat_id, message)
        elif action == 'sell':
            profit = signal[3]
            message = f"Señal de VENTA detectada en {ticker} en {date.strftime('%Y-%m-%d')}. Precio: ${price:.2f}. Rendimiento: {profit:.2f}%."
            send_telegram_message(telegram_token, chat_id, message)

    # Generar y enviar gráfico de rendimiento acumulado
    output_path = 'cumulative_returns.png'
    plot_cumulative_returns(df, signals, output_path)
    send_telegram_photo(telegram_token, chat_id, output_path)


# Programar la ejecución a las 18:00 (hora de Argentina)
def job():
    ticker = 'AAPL'  # Ejemplo de ticker
    period_fast = 10  # Período de la media rápida
    period_slow = 20  # Período de la media lenta
    telegram_token = '7583734248:AAG6ee7QdfbFuQSWEYCL0NNMV5Omn3GpbL4'
    chat_id = '-1002284687068'

    # Ejecutar el bot
    trading_bot(ticker, period_fast, period_slow, telegram_token, chat_id)


# Configurar el timezone de Argentina
argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')

# Programar la tarea para que se ejecute a las 18:00 (hora de Argentina)
schedule.every().day.at("18:00").do(job)

# Ejecutar el loop del scheduler
while True:
    schedule.run_pending()
    time.sleep(60)  # Esperar un minuto antes de la siguiente verificación
