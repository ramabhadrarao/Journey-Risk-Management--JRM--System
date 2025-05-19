# backend/config.py
import os
from datetime import timedelta

# Basic app configuration
APP_ENV = os.getenv('APP_ENV', 'development')
DEBUG = APP_ENV == 'development'
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key')
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

# MongoDB configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/jrm_system')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'jrm_system')

# Redis configuration (for Socket.IO)
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# API Keys
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', '')
HERE_API_KEY = os.getenv('HERE_API_KEY', '')
OPENCELLID_API_KEY = os.getenv('OPENCELLID_API_KEY', '')

# File paths
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
REPORT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
MODEL_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ml_models')

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

# API rate limiting
RATE_LIMIT = {
    'default': '100 per day, 10 per hour',
    'login': '10 per minute',
    'register': '5 per hour'
}

# Model configuration
ML_MODEL_CONFIG = {
    'accident_risk': {
        'model_type': 'ensemble',
        'update_frequency': 24,  # hours
        'features': ['weather', 'traffic', 'time_of_day', 'road_type', 'historical_accidents']
    },
    'eta_optimization': {
        'model_type': 'regression',
        'update_frequency': 1,  # hours
        'features': ['traffic', 'weather', 'vehicle_type', 'road_condition']
    },
    'weather_hazard': {
        'model_type': 'classification',
        'update_frequency': 1,  # hours
        'features': ['precipitation', 'visibility', 'wind_speed', 'temperature']
    },
    'route_safety': {
        'model_type': 'ensemble',
        'update_frequency': 168,  # weekly
        'features': ['road_curvature', 'blind_spots', 'accident_hotspots', 'road_quality']
    },
    'breakdown_prediction': {
        'model_type': 'survival',
        'update_frequency': 24,  # hours
        'features': ['engine_temp', 'oil_pressure', 'mileage', 'maintenance_history']
    },
    'fuel_efficiency': {
        'model_type': 'regression',
        'update_frequency': 24,  # hours
        'features': ['speed', 'acceleration', 'road_grade', 'traffic', 'vehicle_load']
    }
}

# Notification settings
NOTIFICATION_CONFIG = {
    'email': {
        'enabled': True,
        'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', 587)),
        'smtp_username': os.getenv('SMTP_USERNAME', ''),
        'smtp_password': os.getenv('SMTP_PASSWORD', ''),
    },
    'sms': {
        'enabled': bool(os.getenv('SMS_ENABLED', False)),
        'provider': os.getenv('SMS_PROVIDER', 'twilio'),
        'account_sid': os.getenv('TWILIO_ACCOUNT_SID', ''),
        'auth_token': os.getenv('TWILIO_AUTH_TOKEN', ''),
        'phone_number': os.getenv('TWILIO_PHONE_NUMBER', ''),
    },
    'push': {
        'enabled': bool(os.getenv('PUSH_ENABLED', True)),
        'vapid_public_key': os.getenv('VAPID_PUBLIC_KEY', ''),
        'vapid_private_key': os.getenv('VAPID_PRIVATE_KEY', ''),
        'vapid_claim_email': os.getenv('VAPID_CLAIM_EMAIL', ''),
    }
}

# Caching configuration
CACHE_CONFIG = {
    'enabled': True,
    'type': 'redis',
    'expiration': {
        'default': 300,  # 5 minutes
        'routes': 3600,  # 1 hour
        'weather': 1800,  # 30 minutes
        'traffic': 300,  # 5 minutes
    }
}

# Risk thresholds
RISK_THRESHOLDS = {
    'accident': {
        'low': 0.3,
        'medium': 0.6,
        'high': 0.8
    },
    'weather': {
        'low': 0.3,
        'medium': 0.6,
        'high': 0.8
    },
    'breakdown': {
        'low': 0.3,
        'medium': 0.6,
        'high': 0.8
    },
    'route_safety': {
        'low': 3.0,
        'medium': 6.0,
        'high': 8.0
    }
}