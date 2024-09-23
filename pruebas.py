import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from telegram import Bot
import datetime
import time
import schedule
import pytz
import os

# Configuración del bot de Telegram
TELEGRAM_TOKEN = 'TU_TOKEN'
TELEGRAM_CHAT_ID = 'TU_CHAT_ID'

bot = Bot(token=TELEGRAM_TOKEN)

# Función para descargar y procesar datos de varios tickers
def download_data(tickers):
    ticker_data = {}
    for ticker, (short_window, long_window) in tickers.items():
        try:
            print(f"Descargando datos para {ticker}...")  # Log de descarga de datos
            data = yf.download(ticker, period='3mo')
            data['SMA_short'] = data['Close'].rolling(window=short_window).mean()
            data['SMA_long'] = data['Close'].rolling(window=long_window).mean()
            ticker_data[ticker] = data
            print(f"Datos descargados para {ticker}.")  # Confirmación de descarga
        except Exception as e:
            print(f"Error descargando datos para {ticker}: {e}")
    return ticker_data

# Función para enviar mensajes y gráficos a Telegram
def send_telegram_message(message, photo_path=None):
    if photo_path:
        with open(photo_path, 'rb') as photo:
            bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=photo, caption=message)
    else:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)

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
def check_signals(data, ticker):
    data['Position'] = 0
    data['Position'] = data['SMA_short'] > data['SMA_long']
    data['Signal'] = data['Position'].diff()

    data['Return'] = data['Close'].pct_change()  # Rendimiento diario

    last_signal = data['Signal'].iloc[-1]
    last_close_price = data['Close'].iloc[-1]

    if last_signal == 1:  # Señal de compra
        message = f"🟢 Señal de COMPRA para {ticker} - Precio actual: {last_close_price}"
        print(f"Generando señal de compra para {ticker}...")  # Log de señal de compra
        send_telegram_message(message)
    elif last_signal == -1:  # Señal de venta
        last_buy_price = data[data['Signal'] == 1]['Close'].iloc[-1] if not data[data['Signal'] == 1].empty else None
        if last_buy_price:
            performance = (last_close_price - last_buy_price) / last_buy_price * 100
            message = f"🔴 Señal de VENTA para {ticker} - Precio actual: {last_close_price} - Rendimiento: {performance:.2f}%"
            print(f"Generando señal de venta para {ticker}...")  # Log de señal de venta
            photo_path = plot_cumulative_performance(data, ticker)  # Graficar rendimiento acumulado
            send_telegram_message(message, photo_path)  # Enviar mensaje y gráfico
            os.remove(photo_path)  # Eliminar gráfico después de enviarlo
        else:
            message = f"🔴 Señal de VENTA para {ticker} - Precio actual: {last_close_price}"
            send_telegram_message(message)
    else:
        print(f"No hay señales nuevas hoy para {ticker}.")  # Log de no señales
        send_telegram_message(f"No hay señales nuevas hoy para {ticker}")

# Función para ejecutar el bot
def run_bot(tickers):
    print("Ejecutando el bot...")  # Log de inicio del bot
    ticker_data = download_data(tickers)
    for ticker, data in ticker_data.items():
        check_signals(data, ticker)
    print("Bot ejecutado con éxito.")  # Log de finalización del bot

# Job programado
def job():
    print("Ejecutando el trabajo programado...")  # Log al iniciar el trabajo
    tickers = {
        'AAPL': (16, 45),
        'MSFT': (37, 65),
        'GOOGL': (19, 65),
        'GGAL' : (12,45),
        'BTC-USD':(11,45),
    }
    run_bot(tickers)
    print("Trabajo completado.")  # Log al finalizar el trabajo

# Configurar el timezone de Argentina
argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')

# Programar la tarea para que se ejecute cada 24 horas
print("Programando el trabajo...")  # Log de programación
schedule.every(24).hours.do(job)

# Ejecutar el loop del scheduler
while True:
    print("Esperando la próxima tarea...")  # Log de espera antes de la próxima tarea
    schedule.run_pending()
    time.sleep(60)




