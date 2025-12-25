from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import logging

# Configuración del registro
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

# --- CONFIGURACIÓN DE TELEGRAM ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- FUNCIÓN PARA ENVIAR NOTIFICACIÓN CON BOTÓN ---
def send_telegram_notification(message, withdrawal_id):
    if not BOT_TOKEN or not CHAT_ID:
        logging.error("ERROR CRÍTICO: Faltan credenciales de Telegram.")
        return False
    
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
        "reply_markup": keyboard
    }
    
    try:
        logging.info("Intentando enviar notificación con botón...")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logging.info("¡Notificación con botón enviada con éxito!")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al contactar con API de Telegram: {e}", exc_info=True)
        return False

# --- RUTA QUE LLAMA TU APLICACIÓN ---
@app.route("/submit-withdrawal", methods=['POST'])
def handle_withdrawal():
    logging.info("¡CONEXIÓN RECIBIDA desde la app!")
    data = request.get_json(silent=True)

    if not data or not all(k in data for k in ["date", "amount", "binanceId"]):
        logging.error(f"Datos JSON incompletos o mal formados: {data}")
        return jsonify({"status": "error", "message": "Datos mal formados"}), 400

    # Usamos la fecha como un ID simple para este ejemplo
    withdrawal_id = data.get('date').replace(" ", "_") 

    message_text = (
        f"‼️ *Nueva solicitud de retiro* ‼️\n\n"
        f"*Fecha:* `{data.get('date')}`\n"
        f"*Cantidad:* `{data.get('amount')}` puntos\n"
        f"*ID Binance:* `{data.get('binanceId')}`\n\n"
        f"🔵 *Estado:* Pendiente"
    )

    if send_telegram_notification(message_text, withdrawal_id):
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error"}), 500

# --- RUTA PARA QUE TELEGRAM AVISE (WEBHOOK) ---
@app.route("/telegram-webhook", methods=['POST'])
def handle_telegram_updates():
    update = request.get_json()
    
    if "callback_query" in update:
        query = update["callback_query"]
        data = query["data"]
        query_id = query["id"]
        
        if data.startswith("paid_"):
            message = query["message"]
            chat_id = message["chat"]["id"]
            message_id = message["message_id"]
            original_text = message["text"]

            # Reemplazamos el estado en el texto original
            new_text = original_text.replace("🔵 *Estado:* Pendiente", "🟢 *Estado:* Pagado")

            # 1. Editamos el mensaje original en Telegram
            edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": new_text,
                "parse_mode": "Markdown",
                "reply_markup": {"inline_keyboard": []} # Quitamos el botón
            }
            requests.post(edit_url, json=payload)
            
            # 2. Respondemos al clic para que el botón deje de "cargar"
            answer_url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
            requests.post(answer_url, json={"callback_query_id": query_id, "text": "¡Marcado como pagado!"})

    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
