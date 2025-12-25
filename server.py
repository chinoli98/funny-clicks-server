from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import logging
import sqlite3

# --- CONFIGURACIÓN ---
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
CORS(app)
DATABASE_FILE = 'withdrawals.db'

# --- CONFIGURACIÓN DE TELEGRAM ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- FUNCIÓN PARA INICIALIZAR LA BASE DE DATOS ---
def init_db():
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        # Creamos una tabla para guardar los retiros si no existe
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE NOT NULL,
                amount INTEGER NOT NULL,
                binance_id TEXT NOT NULL,
                status TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
        logging.info("Base de datos inicializada correctamente.")
    except Exception as e:
        logging.error(f"Error al inicializar la base de datos: {e}", exc_info=True)

# --- RUTA PARA QUE LA APP ENVÍE UN NUEVO RETIRO ---
@app.route("/submit-withdrawal", methods=['POST'])
def handle_withdrawal():
    data = request.get_json(silent=True)
    if not data or not all(k in data for k in ["date", "amount", "binanceId"]):
        return jsonify({"status": "error", "message": "Datos mal formados"}), 400

    request_id = data.get('date') # Usamos la fecha como ID único para la app
    amount = data.get('amount')
    binance_id = data.get('binanceId')

    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO withdrawals (request_id, amount, binance_id, status) VALUES (?, ?, ?, ?)",
            (request_id, amount, binance_id, 'Pendiente')
        )
        db_id = cursor.lastrowid # Obtenemos el ID numérico de la base de datos
        conn.commit()
        conn.close()
        logging.info(f"Nuevo retiro guardado en la BD con ID: {db_id}")

        message_text = (
            f"‼️ *Nueva solicitud de retiro (ID: {db_id})* ‼️\n\n"
            f"*Fecha:* `{request_id}`\n"
            f"*Cantidad:* `{amount}` puntos\n"
            f"*ID Binance:* `{binance_id}`\n\n"
            f"🔵 *Estado:* Pendiente"
        )
        
        # Enviamos la notificación a Telegram con el botón que usa el ID de la BD
        send_telegram_notification(message_text, db_id)
        return jsonify({"status": "success"})

    except Exception as e:
        logging.error(f"Error al procesar el retiro: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Error interno del servidor"}), 500

# --- RUTA PARA QUE TELEGRAM AVISE CUANDO PULSAS EL BOTÓN ---
@app.route("/telegram-webhook", methods=['POST'])
def handle_telegram_updates():
    update = request.get_json()
    if "callback_query" in update:
        query = update["callback_query"]
        data = query["data"]
        query_id = query["id"]
        
        if data.startswith("paid_"):
            db_id = data.split("_")[1]
            try:
                # Actualiza el estado en la base de datos
                conn = sqlite3.connect(DATABASE_FILE)
                cursor = conn.cursor()
                cursor.execute("UPDATE withdrawals SET status = ? WHERE id = ?", ('Pagado', db_id))
                conn.commit()
                conn.close()
                logging.info(f"Retiro ID {db_id} marcado como 'Pagado' en la BD.")

                # Edita el mensaje original en Telegram
                message = query["message"]
                new_text = message["text"].replace("🔵 *Estado:* Pendiente", "🟢 *Estado:* Pagado")
                edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
                payload = {
                    "chat_id": message["chat"]["id"], "message_id": message["message_id"],
                    "text": new_text, "parse_mode": "Markdown", "reply_markup": {"inline_keyboard": []}
                }
                requests.post(edit_url, json=payload)
                
                # Responde al clic
                answer_url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
                requests.post(answer_url, json={"callback_query_id": query_id, "text": "¡Marcado como pagado!"})
            except Exception as e:
                logging.error(f"Error al procesar el callback de Telegram: {e}", exc_info=True)

    return "ok", 200

# --- NUEVA RUTA PARA QUE LA APP CONSULTE EL ESTADO ---
@app.route("/check-status", methods=['POST'])
def check_status():
    data = request.get_json(silent=True)
    if not data or "request_ids" not in data:
        return jsonify({"error": "Se requiere una lista de 'request_ids'"}), 400

    request_ids = data["request_ids"]
    statuses = {}
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        # Creamos un placeholder '?' por cada ID para una consulta segura
        placeholders = ','.join('?' for _ in request_ids)
        query = f"SELECT request_id, status FROM withdrawals WHERE request_id IN ({placeholders})"
        cursor.execute(query, request_ids)
        rows = cursor.fetchall()
        for row in rows:
            statuses[row[0]] = row[1] # Mapea request_id -> status
        conn.close()
    except Exception as e:
        logging.error(f"Error al consultar estados en la BD: {e}", exc_info=True)
    
    return jsonify(statuses)


# --- INICIO DEL SERVIDOR ---
if __name__ == '__main__':
    init_db() # Se asegura de que la base de datos y la tabla existan al arrancar
    # Gunicorn usará esta configuración para poner el servidor en marcha
    app.run(host="0.0.0.0", port=10000)
