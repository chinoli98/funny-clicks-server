from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import logging

# Configura un registro para ver todo en los logs de Render
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

# --- CONFIGURACIÓN DE TELEGRAM ---
# Lee las credenciales secretas de las variables de entorno de Render
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- FUNCIÓN PARA ENVIAR NOTIFICACIÓN A TELEGRAM ---
def send_telegram_notification(message):
    if not BOT_TOKEN or not CHAT_ID:
        logging.error("ERROR CRÍTICO: No se encontraron las variables de entorno TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en Render.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        logging.info("Intentando enviar notificación a Telegram...")
        response = requests.post(url, json=payload)
        response.raise_for_status() # Lanza un error si la API de Telegram responde con un error (4xx o 5xx)
        logging.info("¡Notificación enviada a Telegram con éxito!")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Error de red al contactar con Telegram: {e}", exc_info=True)
        return False

# --- RUTA QUE LLAMA TU APLICACIÓN ---
@app.route("/submit-withdrawal", methods=['POST'])
def handle_withdrawal():
    logging.info("¡CONEXIÓN RECIBIDA! La ruta /submit-withdrawal fue alcanzada.")
    data = request.get_json(silent=True)

    if not data:
        logging.error("La solicitud no contenía un JSON válido.")
        return jsonify({"status": "error", "message": "Datos mal formados"}), 400

    date = data.get("date")
    amount = data.get("amount")
    binance_id = data.get("binanceId")

    if not all([date, amount, binance_id]):
        logging.error(f"Faltan datos en el JSON recibido: {data}")
        return jsonify({"status": "error", "message": "Faltan datos en la solicitud"}), 400

    logging.info(f"Datos recibidos correctamente: {data}")
    message_text = (
        f"‼️ *Nueva solicitud de retiro* ‼️\n\n"
        f"*Fecha:* `{date}`\n"
        f"*Cantidad:* `{amount}` puntos\n"
        f"*ID Binance:* `{binance_id}`"
    )

    # Intenta enviar el mensaje a Telegram
    telegram_success = send_telegram_notification(message_text)

    if telegram_success:
        logging.info("Respondiendo a la app: Éxito total.")
        return jsonify({"status": "success", "message": "Notificación enviada"})
    else:
        logging.error("Falló el envío a Telegram. Respondiendo error a la app.")
        # Le decimos a la app que algo falló en el último paso
        return jsonify({"status": "error", "message": "El servidor no pudo contactar a Telegram."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
