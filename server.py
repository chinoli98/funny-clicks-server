from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import logging
import threading

# Configura un registro para ver todo en los logs de Render
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

# --- CONFIGURACIÓN DE TELEGRAM ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- MINI BASE DE DATOS (en memoria, para simplicidad) ---
# Usamos un lock para manejar el acceso concurrente al "último ID"
last_withdrawal_id = 0
id_lock = threading.Lock()

# --- FUNCIÓN PARA ENVIAR NOTIFICACIÓN CON BOTÓN ---
def send_telegram_notification_with_button(message, withdrawal_id):
    if not BOT_TOKEN or not CHAT_ID:
        logging.error("ERROR CRÍTICO: Faltan credenciales de Telegram en las variables de entorno.")
        return False
    
    # Creamos el botón con el ID del retiro oculto en 'callback_data'
    # IMPORTANTE: callback_data tiene un límite de 64 bytes
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Marcar como Pagado", "callback_data": f"paid_{withdrawal_id}"}
        ]]
    }

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "reply_markup": keyboard  # <-- ¡Aquí añadimos el botón!
    }
    
    try:
        logging.info("Intentando enviar notificación con botón a Telegram...")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logging.info("¡Notificación con botón enviada con éxito!")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Error de red al contactar con Telegram: {e}", exc_info=True)
        return False

# --- RUTA QUE LLAMA TU APLICACIÓN ---
@app.route("/submit-withdrawal", methods=['POST'])
def handle_withdrawal():
    global last_withdrawal_id
    logging.info("¡CONEXIÓN RECIBIDA!")
    data = request.get_json(silent=True)

    if not data:
        logging.error("La solicitud no contenía un JSON válido.")
        return jsonify({"status": "error", "message": "Datos mal formados"}), 400

    # Generamos un ID único para este retiro
    with id_lock:
        last_withdrawal_id += 1
        new_id = last_withdrawal_id

    # Preparamos el mensaje
    message_text = (
        f"‼️ *Nueva solicitud de retiro (ID: {new_id})* ‼️\n\n"
        f"*Fecha:* `{data.get('date')}`\n"
        f"*Cantidad:* `{data.get('amount')}` puntos\n"
        f"*ID Binance:* `{data.get('binanceId')}`\n\n"
        f"🔵 *Estado:* Pendiente"
    )

    # Enviamos el mensaje a Telegram con el botón
    telegram_success = send_telegram_notification_with_button(message_text, new_id)

    if telegram_success:
        logging.info("Respondiendo a la app: Éxito total.")
        return jsonify({"status": "success", "message": "Notificación enviada"})
    else:
        logging.error("Falló el envío a Telegram. Respondiendo error a la app.")
        return jsonify({"status": "error", "message": "El servidor no pudo contactar a Telegram."}), 500

# --- CÓDIGO PARA MANEJAR EL BOTÓN (Parte Avanzada) ---
# Esta es una sección conceptual. Implementarla requiere un webhook.
# Cuando pulsas el botón, Telegram envía una petición a una URL que tú configuras.
@app.route("/telegram-webhook", methods=['POST'])
def handle_telegram_updates():
    update = request.get_json()
    
    if "callback_query" in update:
        query = update["callback_query"]
        data = query["data"] # ej: "paid_123"
        chat_id = query["message"]["chat"]["id"]
        message_id = query["message"]["message_id"]
        
        if data.startswith("paid_"):
            withdrawal_id = data.split("_")[1]
            
            # Aquí buscarías el retiro en tu base de datos y lo actualizarías
            # ...
            
            # Editas el mensaje original para que muestre el nuevo estado
            new_text = f"✅ *Retiro Pagado (ID: {withdrawal_id})* ✅" # (Texto simplificado)
            edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": new_text,
                "parse_mode": "Markdown"
            }
            requests.post(edit_url, json=payload)
            
            # Respondes a Telegram para que el botón deje de cargar
            answer_url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
            requests.post(answer_url, json={"callback_query_id": query["id"], "text": "¡Marcado como pagado!"})

    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
