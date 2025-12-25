from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

# Configura un registro muy detallado
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
# Habilita CORS para ser más tolerante a las conexiones
CORS(app)

# Ruta para verificar desde un navegador
@app.route("/")
def health_check():
    logging.info("Ruta principal '/' fue visitada (Health Check).")
    return "El servidor de Funny Clicks está funcionando y listo."

# Ruta para recibir las solicitudes de retiro
@app.route("/submit-withdrawal", methods=['POST'])
def handle_withdrawal():
    # Este es el primer mensaje que deberíamos ver si la app conecta
    logging.info("¡CONEXIÓN RECIBIDA! La ruta /submit-withdrawal fue alcanzada.")
    
    try:
        # Intenta obtener los datos JSON
        data = request.get_json(silent=True)
        if data:
            logging.info(f"Datos JSON recibidos con éxito: {data}")
        else:
            # Si no hay JSON, registra los datos en bruto que llegaron
            raw_data = request.data
            logging.warning(f"No se pudo decodificar JSON. Datos en bruto recibidos: {raw_data}")
        
        # Responde a la app que todo está bien
        logging.info("Enviando respuesta de éxito a la app.")
        return jsonify({"status": "success", "message": "Servidor recibió la petición."})

    except Exception as e:
        # Si algo dentro de esta función falla, lo registrará
        logging.error(f"¡ERROR DENTRO DE LA FUNCIÓN! -> {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Error interno del servidor."}), 500

if __name__ == "__main__":
    # Gunicorn usará esta configuración
    app.run(host="0.0.0.0", port=10000)
