# backend/app.py
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_pymongo import PyMongo
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import logging
from logging.handlers import RotatingFileHandler
from apscheduler.schedulers.background import BackgroundScheduler

from config import (
    APP_ENV, DEBUG, SECRET_KEY, JWT_SECRET_KEY, 
    MONGO_URI, RATE_LIMIT, REDIS_URL
)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
app.config['MONGO_URI'] = MONGO_URI
app.config['DEBUG'] = DEBUG

# Setup CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize JWT
jwt = JWTManager(app)

# Initialize MongoDB
mongo = PyMongo(app)
db = mongo.db

# Initialize Socket.IO with Redis for scaling
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent', message_queue=REDIS_URL)

# Setup rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[RATE_LIMIT['default']],
    storage_uri=REDIS_URL
)

# Configure logging
if not os.path.exists('logs'):
    os.mkdir('logs')

file_handler = RotatingFileHandler('logs/jrm_system.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)

app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('JRM System startup')

# Initialize scheduler for background tasks
scheduler = BackgroundScheduler()

# Register blueprints
from api.auth import auth_bp
from api.routes import routes_bp
from api.risk_analysis import risk_bp
from api.weather import weather_bp
from api.vehicles import vehicles_bp
from api.dashboard import dashboard_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(routes_bp, url_prefix='/api/routes')
app.register_blueprint(risk_bp, url_prefix='/api/risk')
app.register_blueprint(weather_bp, url_prefix='/api/weather')
app.register_blueprint(vehicles_bp, url_prefix='/api/vehicles')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'Server Error: {error}')
    return jsonify({'error': 'Internal server error'}), 500

# Schedule background tasks
from services.accident_prediction import update_accident_model
from services.weather_service import update_weather_data
from services.route_safety import update_route_safety
from services.eta_optimizer import update_eta_model

def init_scheduler():
    scheduler.add_job(update_accident_model, 'interval', hours=24)
    scheduler.add_job(update_weather_data, 'interval', minutes=30)
    scheduler.add_job(update_route_safety, 'interval', hours=168)  # weekly
    scheduler.add_job(update_eta_model, 'interval', hours=1)
    
    # Start the scheduler
    scheduler.start()

# Socket.IO events
@socketio.on('connect')
def handle_connect():
    app.logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    app.logger.info('Client disconnected')

@socketio.on('subscribe')
def handle_subscribe(data):
    """Handle subscription to real-time updates for a specific route or vehicle"""
    if 'route_id' in data:
        socketio.emit('subscription_success', {'message': f"Subscribed to route {data['route_id']}"})
    elif 'vehicle_id' in data:
        socketio.emit('subscription_success', {'message': f"Subscribed to vehicle {data['vehicle_id']}"})

if __name__ == '__main__':
    init_scheduler()
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=DEBUG)