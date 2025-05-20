# Fix for models/user.py
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from bson.objectid import ObjectId
from models import db

class User:
    @staticmethod
    def create(username, email, password, role='user', company=None):
        """Create a new user"""
        user = {
            'username': username,
            'email': email,
            'password_hash': generate_password_hash(password),
            'role': role,
            'company': company,
            'created_at': datetime.datetime.utcnow(),
            'last_login': None,
            'preferences': {
                'notifications': {
                    'email': True,
                    'sms': False,
                    'push': True
                },
                'dashboard': {
                    'default_view': 'map',
                    'risk_threshold': 'medium'
                }
            }
        }
        
        result = db.users.insert_one(user)
        user['_id'] = result.inserted_id
        return user
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        return db.users.find_one({'_id': user_id})
    
    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        return db.users.find_one({'username': username})
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        return db.users.find_one({'email': email})
    
    @staticmethod
    def check_password(user, password):
        """Check password for user"""
        if not user or 'password_hash' not in user:
            return False
        return check_password_hash(user['password_hash'], password)
    
    @staticmethod
    def update_last_login(user_id):
        """Update last login timestamp"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        db.users.update_one(
            {'_id': user_id},
            {'$set': {'last_login': datetime.datetime.utcnow()}}
        )