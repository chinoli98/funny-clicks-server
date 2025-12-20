from flask import Flask, request, jsonify
import requests
import os

# --- CONFIGURACIÓN ---
# Lee las credenciales secretas de las variables de entorno de Render
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Crea la aplicación del servidor
app = Flask(__name__)

# --- FUNCIÓN PARA ENVIAR NOTIFICACIONES ---
def send_telegram_notification(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("ERROR: Faltan las credenciales de Telegram en las variables de entorno de Render.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status() 
        print("Notificación enviada a Telegram con éxito.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error al contactar con la API de Telegram: {e}")
        return False

# --- EL ENDPOINT QUE TU APP VA A LLAMAR ---
@app.route("/submit-withdrawal", methods=["POST"])
def handle_withdrawal():
    # 1. Recibir los datos que envía la app
    data = request.get_json()
    if not data:
        print("ERROR: No se recibieron datos JSON en la petición.")
        return jsonify({"status": "error", "message": "No se recibieron datos"}), 400

    date = data.get("date")
    amount = data.get("amount")
    binance_id = data.get("binanceId")

    if not all([date, amount, binance_id]):
        print("ERROR: Faltan datos en el JSON recibido.")
        return jsonify({"status": "error", "message": "Faltan datos en la solicitud"}), 400

    # 2. Preparar el mensaje para Telegram
    message_text = (
        f"‼️ *Nueva solicitud de retiro* ‼️\n\n"
        f"*Fecha:* `{date}`\n"
        f"*Cantidad:* `{amount}` puntos\n"
        f"*ID Binance:* `{binance_id}`"
    )

    # 3. Enviar la notificación
    success = send_telegram_notification(message_text)

    # 4. Responder a la aplicación
    if success:
        print("Respondiendo a la app: Éxito")
        return jsonify({"status": "success", "message": "Notificación enviada"})
    else:
        print("Respondiendo a la app: Error del servidor")
        return jsonify({"status": "error", "message": "No se pudo enviar la notificación de Telegram"}), 500

# --- EJECUTAR EL SERVIDOR ---
if __name__ == "__main__":
    # Render usa esta configuración para poner el servidor en marcha
    app.run(host="0.0.0.0", port=10000)
