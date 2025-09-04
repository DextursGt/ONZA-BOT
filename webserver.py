"""
Webserver para mantener el bot activo 24/7
Este servidor web simple evita que el bot se "duerma" en servicios gratuitos
"""

from flask import Flask, jsonify
from threading import Thread
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Crear la aplicación Flask
app = Flask(__name__)

@app.route('/')
def index():
    """Página principal - muestra el estado del bot"""
    return '''
    <html>
        <head>
            <title>ONZA Bot - Estado</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    margin: 0;
                    padding: 20px;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .container {
                    text-align: center;
                    background: rgba(255,255,255,0.1);
                    padding: 40px;
                    border-radius: 20px;
                    backdrop-filter: blur(10px);
                    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                }
                h1 { color: #00E5A8; margin-bottom: 20px; }
                .status { 
                    font-size: 24px; 
                    color: #4CAF50; 
                    margin: 20px 0;
                    animation: pulse 2s infinite;
                }
                @keyframes pulse {
                    0% { opacity: 1; }
                    50% { opacity: 0.7; }
                    100% { opacity: 1; }
                }
                .info { margin: 10px 0; opacity: 0.8; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 ONZA Bot</h1>
                <div class="status">🟢 Bot Activo</div>
                <div class="info">Servidor web funcionando correctamente</div>
                <div class="info">Bot de Discord online 24/7</div>
                <div class="info">Versión: 3.0</div>
            </div>
        </body>
    </html>
    '''

@app.route('/status')
def status():
    """Endpoint de estado para monitoreo"""
    return jsonify({
        'status': 'online',
        'bot': 'ONZA Bot',
        'version': '3.0',
        'message': 'Bot funcionando correctamente'
    })

@app.route('/health')
def health():
    """Endpoint de salud para servicios de monitoreo"""
    return jsonify({
        'healthy': True,
        'timestamp': '2024-01-01T00:00:00Z'
    })

def run():
    """Ejecutar el servidor Flask"""
    try:
        log.info("🌐 Iniciando servidor web Flask...")
        app.run(
            host='0.0.0.0',  # Aceptar conexiones de cualquier IP
            port=8000,       # Puerto 8000
            debug=False,     # Desactivar debug en producción
            threaded=True    # Permitir múltiples hilos
        )
    except Exception as e:
        log.error(f"❌ Error iniciando servidor web: {e}")

def keep_alive():
    """Mantener el bot activo iniciando el servidor web en un hilo separado"""
    try:
        log.info("🔄 Iniciando keep-alive server...")
        server = Thread(target=run, daemon=True)  # daemon=True para que se cierre con el programa principal
        server.start()
        log.info("✅ Keep-alive server iniciado correctamente")
    except Exception as e:
        log.error(f"❌ Error iniciando keep-alive: {e}")

if __name__ == "__main__":
    # Si se ejecuta directamente, iniciar el servidor
    keep_alive()
    # Mantener el programa corriendo
    import time
    while True:
        time.sleep(1)
