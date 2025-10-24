from flask import Flask
from flask_socketio import SocketIO
from kafka_consumer import init_kafka
from routes import main
import os

# Initialize SocketIO (will be configured in create_app)
socketio = SocketIO()

def create_app():
    template_dir = os.path.abspath('templates')
    static_dir = os.path.abspath('static')
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    
    # Configure SocketIO
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')

    # Register route blueprints to enable request handling
    app.register_blueprint(main)

    # Initialize Kafka consumer for streaming data processing
    init_kafka()

    return app
