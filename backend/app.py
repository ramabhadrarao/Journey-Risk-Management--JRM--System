#!/usr/bin/env python
# backend/app.py (Modified - Final Version)
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
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

# Initialize MongoDB by importing and calling the init_db function
from models import init_db
db = init_db(app)

# Initialize Socket.IO with Redis for scaling
try:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent', message_queue=REDIS_URL)
except Exception as e:
    app.logger.warning(f"Error initializing SocketIO with Redis: {str(e)}")
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# Setup rate limiting
try:
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=[RATE_LIMIT['default']],
        storage_uri=REDIS_URL
    )
    app.limiter = limiter  # Attach limiter to app for access in blueprints
except Exception as e:
    app.logger.warning(f"Error initializing rate limiter: {str(e)}")
    app.limiter = None

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

# Import and register blueprints
from api.auth import auth_bp, apply_rate_limits

# Register auth blueprint
app.register_blueprint(auth_bp, url_prefix='/api/auth')

# Apply rate limits to auth blueprint
apply_rate_limits(app)

# Import and register other blueprints if they exist
try:
    from api.routes import routes_bp
    app.register_blueprint(routes_bp, url_prefix='/api/routes')
    app.logger.info("Registered routes_bp blueprint")
except ImportError as e:
    app.logger.warning(f"routes_bp blueprint not available: {str(e)}")

try:
    from api.risk_analysis import risk_bp
    app.register_blueprint(risk_bp, url_prefix='/api/risk')
    app.logger.info("Registered risk_bp blueprint")
except ImportError as e:
    app.logger.warning(f"risk_bp blueprint not available: {str(e)}")

try:
    from api.weather import weather_bp
    app.register_blueprint(weather_bp, url_prefix='/api/weather')
    app.logger.info("Registered weather_bp blueprint")
except ImportError as e:
    app.logger.warning(f"weather_bp blueprint not available: {str(e)}")

try:
    from api.vehicles import vehicles_bp
    app.register_blueprint(vehicles_bp, url_prefix='/api/vehicles')
    app.logger.info("Registered vehicles_bp blueprint")
except ImportError as e:
    app.logger.warning(f"vehicles_bp blueprint not available: {str(e)}")

try:
    from api.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.logger.info("Registered dashboard_bp blueprint")
except ImportError as e:
    app.logger.warning(f"dashboard_bp blueprint not available: {str(e)}")

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'Server Error: {error}')
    return jsonify({'error': 'Internal server error'}), 500

# Schedule background tasks
try:
    from services.accident_prediction import update_accident_model
    from services.weather_service import update_weather_data
    from services.route_safety import update_route_safety
    from services.eta_optimizer import update_eta_model

    def init_scheduler():
        try:
            scheduler.add_job(update_accident_model, 'interval', hours=24)
            scheduler.add_job(update_weather_data, 'interval', minutes=30)
            scheduler.add_job(update_route_safety, 'interval', hours=168)  # weekly
            scheduler.add_job(update_eta_model, 'interval', hours=1)
            
            # Start the scheduler
            scheduler.start()
            app.logger.info("Background scheduler started successfully")
        except Exception as e:
            app.logger.error(f"Error starting scheduler: {str(e)}")
except ImportError:
    app.logger.warning("Some background task modules are not available")
    
    def init_scheduler():
        app.logger.warning("Scheduler initialization skipped due to missing modules")

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

# At the end of your app.py file, make sure it looks like this:
if __name__ == '__main__':
    init_scheduler()
    app.run(host='0.0.0.0', port=5000, debug=True)

    # socketio.run(
    #     app,
    #     host='0.0.0.0',  # Important: This binds to all interfaces
    #     port=int(os.environ.get('PORT', 5000)),
    #     debug=True
    # )