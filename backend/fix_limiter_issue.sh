#!/bin/bash
# fix_limiter_issue.sh - Fix the limiter issue in auth.py

echo "Fixing the limiter issue in auth.py..."

# Update auth.py with fixed rate limit application
cat > api/auth.py << 'EOL'
# backend/api/auth.py (Fixed)
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, 
    jwt_required, get_jwt_identity
)
from models.user import User
from config import RATE_LIMIT

auth_bp = Blueprint('auth', __name__)

# We'll apply rate limits after the blueprint is registered with the app

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['username', 'email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing {field} field"}), 400
    
    # Check if username or email already exists
    if User.get_by_username(data['username']):
        return jsonify({"error": "Username already exists"}), 409
    
    if User.get_by_email(data['email']):
        return jsonify({"error": "Email already exists"}), 409
    
    # Create user
    user = User.create(
        username=data['username'],
        email=data['email'],
        password=data['password'],
        role=data.get('role', 'user'),
        company=data.get('company')
    )
    
    # Create JWT tokens
    access_token = create_access_token(identity=str(user['_id']))
    refresh_token = create_refresh_token(identity=str(user['_id']))
    
    return jsonify({
        "message": "User registered successfully",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": str(user['_id']),
            "username": user['username'],
            "email": user['email'],
            "role": user['role']
        }
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login"""
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400
    
    data = request.get_json()
    
    # Check for username/email and password
    if not data.get('username') and not data.get('email'):
        return jsonify({"error": "Missing username or email"}), 400
    
    if not data.get('password'):
        return jsonify({"error": "Missing password"}), 400
    
    # Find user by username or email
    user = None
    if data.get('username'):
        user = User.get_by_username(data['username'])
    else:
        user = User.get_by_email(data['email'])
    
    # Verify password
    if not user or not User.check_password(user, data['password']):
        return jsonify({"error": "Invalid credentials"}), 401
    
    # Update last login
    User.update_last_login(user['_id'])
    
    # Create JWT tokens
    access_token = create_access_token(identity=str(user['_id']))
    refresh_token = create_refresh_token(identity=str(user['_id']))
    
    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": str(user['_id']),
            "username": user['username'],
            "email": user['email'],
            "role": user['role']
        }
    }), 200

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    current_user = get_jwt_identity()
    access_token = create_access_token(identity=current_user)
    
    return jsonify({
        "access_token": access_token
    }), 200

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    """Get user profile"""
    current_user_id = get_jwt_identity()
    user = User.get_by_id(current_user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "id": str(user['_id']),
        "username": user['username'],
        "email": user['email'],
        "role": user['role'],
        "company": user.get('company'),
        "last_login": user.get('last_login'),
        "preferences": user.get('preferences', {})
    }), 200

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400
    
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # Get current user
    user = User.get_by_id(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Fields that can be updated
    updatable_fields = ['email', 'company', 'preferences']
    update_data = {}
    
    for field in updatable_fields:
        if field in data:
            update_data[field] = data[field]
    
    # Check if email is being changed and if it already exists
    if 'email' in update_data and update_data['email'] != user['email']:
        if User.get_by_email(update_data['email']):
            return jsonify({"error": "Email already exists"}), 409
    
    # Update user
    if update_data:
        from models import db
        from bson.objectid import ObjectId
        db.users.update_one(
            {'_id': ObjectId(current_user_id)},
            {'$set': update_data}
        )
    
    # Get updated user
    updated_user = User.get_by_id(current_user_id)
    
    return jsonify({
        "message": "Profile updated successfully",
        "user": {
            "id": str(updated_user['_id']),
            "username": updated_user['username'],
            "email": updated_user['email'],
            "role": updated_user['role'],
            "company": updated_user.get('company'),
            "preferences": updated_user.get('preferences', {})
        }
    }), 200

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400
    
    data = request.get_json()
    current_user_id = get_jwt_identity()
    
    # Validate required fields
    if not data.get('current_password') or not data.get('new_password'):
        return jsonify({"error": "Missing current_password or new_password"}), 400
    
    # Get current user
    user = User.get_by_id(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Verify current password
    if not User.check_password(user, data['current_password']):
        return jsonify({"error": "Current password is incorrect"}), 401
    
    # Update password
    from models import db
    from bson.objectid import ObjectId
    from werkzeug.security import generate_password_hash
    
    db.users.update_one(
        {'_id': ObjectId(current_user_id)},
        {'$set': {'password_hash': generate_password_hash(data['new_password'])}}
    )
    
    return jsonify({
        "message": "Password changed successfully"
    }), 200

# Fixed function to apply rate limits after the blueprint is registered with the app
def apply_rate_limits(app):
    """Apply rate limits to auth routes"""
    # Check if limiter is available
    if hasattr(app, 'limiter'):
        # Get register endpoint
        register_endpoint = auth_bp.name + '.register'
        login_endpoint = auth_bp.name + '.login'
        
        # Apply rate limits
        app.limiter.limit(RATE_LIMIT['register'])(register)
        app.limiter.limit(RATE_LIMIT['login'])(login)
    else:
        app.logger.warning("Limiter not available, rate limits not applied")
EOL

# Update app.py to fix the limiter reference
cat > app.py << 'EOL'
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

if __name__ == '__main__':
    init_scheduler()
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=DEBUG)
EOL

echo "Fixed limiter issues in auth.py and app.py"
echo "Try running the application with: python run.py"