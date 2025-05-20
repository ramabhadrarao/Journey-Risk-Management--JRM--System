from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.vehicle import Vehicle
from models.telemetry import Telemetry
from bson import ObjectId, json_util
import json

vehicles_bp = Blueprint('vehicles', __name__)

def json_response(data):
    return json.loads(json_util.dumps(data))

@vehicles_bp.route('/', methods=['GET'])
@jwt_required()
def get_vehicles():
    """Get user vehicles"""
    current_user_id = get_jwt_identity()
    
    # Get vehicles
    vehicles = Vehicle.get_by_user(current_user_id)
    
    return jsonify({
        "vehicles": json_response(vehicles)
    }), 200

@vehicles_bp.route('/', methods=['POST'])
@jwt_required()
def create_vehicle():
    """Create a new vehicle"""
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400
    
    data = request.get_json()
    current_user_id = get_jwt_identity()
    
    # Validate required fields
    required_fields = ['name', 'type', 'make', 'model']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing {field} field"}), 400
    
    # Create vehicle
    vehicle = Vehicle.create(current_user_id, data)
    
    return jsonify({
        "message": "Vehicle created successfully",
        "vehicle": json_response(vehicle)
    }), 201

@vehicles_bp.route('/<vehicle_id>', methods=['GET'])
@jwt_required()
def get_vehicle(vehicle_id):
    """Get vehicle by ID"""
    current_user_id = get_jwt_identity()
    
    # Get vehicle
    vehicle = Vehicle.get_by_id(vehicle_id)
    
    if not vehicle:
        return jsonify({"error": "Vehicle not found"}), 404
    
    # Check if user owns the vehicle (unless admin)
    from models import db
    user = db.users.find_one({'_id': ObjectId(current_user_id)})
    if str(vehicle['user_id']) != current_user_id and user.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    # Get telemetry data
    telemetry = Telemetry.get_by_vehicle(vehicle['_id'], limit=100)
    
    # Get latest telemetry
    latest_telemetry = Telemetry.get_latest_by_vehicle(vehicle['_id'])
    
    return jsonify({
        "vehicle": json_response(vehicle),
        "latest_telemetry": json_response(latest_telemetry),
        "telemetry": json_response(telemetry)
    }), 200

@vehicles_bp.route('/<vehicle_id>', methods=['PUT'])
@jwt_required()
def update_vehicle(vehicle_id):
    """Update vehicle"""
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400
    
    data = request.get_json()
    current_user_id = get_jwt_identity()
    
    # Get vehicle
    vehicle = Vehicle.get_by_id(vehicle_id)
    
    if not vehicle:
        return jsonify({"error": "Vehicle not found"}), 404
    
    # Check if user owns the vehicle (unless admin)
    from models import db
    user = db.users.find_one({'_id': ObjectId(current_user_id)})
    if str(vehicle['user_id']) != current_user_id and user.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    # Update vehicle
    updated_vehicle = Vehicle.update(vehicle_id, data)
    
    return jsonify({
        "message": "Vehicle updated successfully",
        "vehicle": json_response(updated_vehicle)
    }), 200

@vehicles_bp.route('/<vehicle_id>', methods=['DELETE'])
@jwt_required()
def delete_vehicle(vehicle_id):
    """Delete vehicle"""
    current_user_id = get_jwt_identity()
    
    # Get vehicle
    vehicle = Vehicle.get_by_id(vehicle_id)
    
    if not vehicle:
        return jsonify({"error": "Vehicle not found"}), 404
    
    # Check if user owns the vehicle (unless admin)
    from models import db
    user = db.users.find_one({'_id': ObjectId(current_user_id)})
    if str(vehicle['user_id']) != current_user_id and user.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    # Delete vehicle
    Vehicle.delete(vehicle_id)
    
    return jsonify({
        "message": "Vehicle deleted successfully"
    }), 200

@vehicles_bp.route('/<vehicle_id>/maintenance', methods=['POST'])
@jwt_required()
def add_maintenance_record(vehicle_id):
    """Add maintenance record to vehicle"""
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400
    
    data = request.get_json()
    current_user_id = get_jwt_identity()
    
    # Validate required fields
    required_fields = ['date', 'type', 'description']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing {field} field"}), 400
    
    # Get vehicle
    vehicle = Vehicle.get_by_id(vehicle_id)
    
    if not vehicle:
        return jsonify({"error": "Vehicle not found"}), 404
    
    # Check if user owns the vehicle (unless admin)
    from models import db
    user = db.users.find_one({'_id': ObjectId(current_user_id)})
    if str(vehicle['user_id']) != current_user_id and user.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    # Add maintenance record
    updated_vehicle = Vehicle.add_maintenance_record(vehicle_id, data)
    
    return jsonify({
        "message": "Maintenance record added successfully",
        "vehicle": json_response(updated_vehicle)
    }), 200

@vehicles_bp.route('/<vehicle_id>/telemetry', methods=['POST'])
@jwt_required()
def add_telemetry(vehicle_id):
    """Add telemetry data for a vehicle"""
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400
    
    data = request.get_json()
    current_user_id = get_jwt_identity()
    
    # Get vehicle
    vehicle = Vehicle.get_by_id(vehicle_id)
    
    if not vehicle:
        return jsonify({"error": "Vehicle not found"}), 404
    
    # Check if user owns the vehicle (unless admin)
    from models import db
    user = db.users.find_one({'_id': ObjectId(current_user_id)})
    if str(vehicle['user_id']) != current_user_id and user.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    # Extract route_id if provided
    route_id = data.pop('route_id', None)
    
    # Add telemetry record
    telemetry = Telemetry.add_record(vehicle_id, route_id, data)
    
    # Emit real-time update via Socket.IO
    from app import socketio
    socketio.emit(f'vehicle_update_{vehicle_id}', {
        'telemetry': json_response(telemetry)
    })
    
    return jsonify({
        "message": "Telemetry data added successfully",
        "telemetry": json_response(telemetry)
    }), 201

@vehicles_bp.route('/<vehicle_id>/telemetry', methods=['GET'])
@jwt_required()
def get_telemetry(vehicle_id):
    """Get telemetry data for a vehicle"""
    current_user_id = get_jwt_identity()
    
    # Parse query parameters
    limit = int(request.args.get('limit', 100))
    skip = int(request.args.get('skip', 0))
    
    # Get vehicle
    vehicle = Vehicle.get_by_id(vehicle_id)
    
    if not vehicle:
        return jsonify({"error": "Vehicle not found"}), 404
    
    # Check if user owns the vehicle (unless admin)
    from models import db
    user = db.users.find_one({'_id': ObjectId(current_user_id)})
    if str(vehicle['user_id']) != current_user_id and user.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    # Get telemetry data
    telemetry = Telemetry.get_by_vehicle(vehicle_id, limit=limit, skip=skip)
    
    return jsonify({
        "telemetry": json_response(telemetry),
        "count": len(telemetry),
        "limit": limit,
        "skip": skip
    }), 200
