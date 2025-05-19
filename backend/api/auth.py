# backend/api/auth.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, 
    jwt_required, get_jwt_identity
)
from models.user import User
from config import RATE_LIMIT

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
@current_app.limiter.limit(RATE_LIMIT['register'])
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
@current_app.limiter.limit(RATE_LIMIT['login'])
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
    db.users.update_one(
        {'_id': ObjectId(current_user_id)},
        {'$set': {'password_hash': generate_password_hash(data['new_password'])}}
    )
    
    return jsonify({
        "message": "Password changed successfully"
    }), 200