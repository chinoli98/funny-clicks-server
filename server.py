from flask import Flask, request, jsonify
import logging

# Configura un registro básico para ver todo en los logs de Render
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Una ruta de prueba para verificar si el servidor está vivo desde un navegador
@app.route("/")
def health_check():
    logging.info("¡El servidor está vivo! Se ha accedido a la ruta principal.")
    return "El servidor de Funny Clicks está funcionando."

# La ruta que llama tu aplicación
@app.route("/submit-withdrawal", methods=["POST"])
def handle_withdrawal():
    logging.info("¡ÉXITO! Se ha recibido una solicitud de retiro desde la app.")
    data = request.get_json(silent=True)
    if data:
        logging.info(f"Datos recibidos: {data}")
    else:
        logging.info("La solicitud no contenía datos JSON.")
    
    # Siempre responde que todo fue bien para esta prueba
    logging.info("Enviando respuesta de éxito a la app.")
    return jsonify({"status": "success", "message": "Prueba del servidor exitosa"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
