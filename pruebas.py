import yfinance as yf
import pandas as pd
import talib
import matplotlib.pyplot as plt
from telegram import Bot
import datetime
import time
import schedule
import pytz
import asyncio
import os

# Configuración del bot de Telegram
TELEGRAM_TOKEN = '7583734248:AAG6ee7QdfbFuQSWEYCL0NNMV5Omn3GpbL4'
TELEGRAM_CHAT_ID = '-1002284687068'

bot = Bot(token=TELEGRAM_TOKEN)

# Función para descargar y procesar datos de varios tickers
def download_data(tickers, short_window, long_window):
    ticker_data = {}
    for ticker in tickers:
        try:
            data = yf.download(ticker, period='3mo')
            data['SMA_short'] = talib.SMA(data['Close'], timeperiod=short_window)
            data['SMA_long'] = talib.SMA(data['Close'], timeperiod=long_window)
            ticker_data[ticker] = data
        except Exception as e:
            print(f"Error descargando datos para {ticker}: {e}")
    return ticker_data

# Función para enviar mensajes y gráficos a Telegram
async def send_telegram_message(message, photo_path=None):
    if photo_path:
        with open(photo_path, 'rb') as photo:
            await bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=photo, caption=message)
    else:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)

# Función para graficar rendimiento acumulado
def plot_cumulative_performance(data, ticker):
    data['Cumulative Return'] = (1 + data['Return']).cumprod() - 1
    plt.figure(figsize=(10, 5))
    plt.plot(data['Cumulative Return'], label=f'Rendimiento Acumulado: {ticker}')
    plt.title(f'Rendimiento Acumulado de {ticker}')
    plt.xlabel('Fecha')
    plt.ylabel('Rendimiento Acumulado')
    plt.legend()
    plt.grid()
    photo_path = f'{ticker}_cumulative_performance.png'
    plt.savefig(photo_path)
    plt.close()
    return photo_path

# Función para generar señales de compra y venta
async def check_signals(data, ticker):
    data['Position'] = 0
    data['Position'] = data['SMA_short'] > data['SMA_long']
    data['Signal'] = data['Position'].diff()

    data['Return'] = data['Close'].pct_change()  # Rendimiento diario

    last_signal = data['Signal'].iloc[-1]
    last_close_price = data['Close'].iloc[-1]

    if last_signal == 1:  # Señal de compra
        message = f"🟢 Señal de COMPRA para {ticker} - Precio actual: {last_close_price}"
        await send_telegram_message(message)
    elif last_signal == -1:  # Señal de venta
        last_buy_price = data[data['Signal'] == 1]['Close'].iloc[-1] if not data[data['Signal'] == 1].empty else None
        if last_buy_price:
            performance = (last_close_price - last_buy_price) / last_buy_price * 100
            message = f"🔴 Señal de VENTA para {ticker} - Precio actual: {last_close_price} - Rendimiento: {performance:.2f}%"
            photo_path = plot_cumulative_performance(data, ticker)  # Graficar rendimiento acumulado
            await send_telegram_message(message, photo_path)  # Enviar mensaje y gráfico
            os.remove(photo_path)  # Eliminar gráfico después de enviarlo
        else:
            message = f"🔴 Señal de VENTA para {ticker} - Precio actual: {last_close_price}"
            await send_telegram_message(message)
    else:
        await send_telegram_message("No hay señales nuevas hoy")

# Función para ejecutar el bot
async def run_bot(tickers, short_window, long_window):
    ticker_data = download_data(tickers, short_window, long_window)
    for ticker, data in ticker_data.items():
        await check_signals(data, ticker)

# Job programado
def job():
    tickers = ['AAPL', 'MSFT', 'GOOGL','BTC-USD','GGAL']
    short_window = 20
    long_window = 50
    asyncio.run(run_bot(tickers, short_window, long_window))

# Configurar el timezone de Argentina
argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')

# Programar la tarea para que se ejecute a las 18:00 (hora de Argentina)
schedule.every().day.at("18:00").do(job)

# Ejecutar el loop del scheduler
while True:
    schedule.run_pending()
    time.sleep(60)



