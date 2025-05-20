from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.route import Route
from models.risk_data import RiskData

risk_bp = Blueprint('risk', __name__)

@risk_bp.route('/analyze/<route_id>', methods=['GET'])
@jwt_required()
def analyze_risk(route_id):
    """Get risk analysis for a specific route"""
    current_user_id = get_jwt_identity()
    
    # Get route
    route = Route.get_by_id(route_id)
    
    if not route:
        return jsonify({"error": "Route not found"}), 404
    
    # Check if user owns the route (unless admin)
    from models import db
    from bson.objectid import ObjectId
    user = db.users.find_one({'_id': ObjectId(current_user_id)})
    if str(route['user_id']) != current_user_id and user.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    # Get risk data
    risk_data = RiskData.get_by_route_id(route_id)
    
    if not risk_data:
        return jsonify({"error": "Risk data not found"}), 404
    
    # Process risk data for analysis
    from services.route_safety import assess_risk_points, get_safety_recommendations
    
    risk_assessment = assess_risk_points(risk_data)
    recommendations = get_safety_recommendations(risk_data)
    
    return jsonify({
        "route_id": route_id,
        "risk_assessment": risk_assessment,
        "recommendations": recommendations
    }), 200

@risk_bp.route('/hotspots', methods=['GET'])
@jwt_required()
def get_risk_hotspots():
    """Get risk hotspots in a geographical area"""
    # Extract query parameters
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    radius = request.args.get('radius', 10)  # Default 10 km
    
    if not lat or not lng:
        return jsonify({"error": "Missing lat or lng parameters"}), 400
    
    try:
        lat = float(lat)
        lng = float(lng)
        radius = float(radius)
    except ValueError:
        return jsonify({"error": "Invalid parameter values"}), 400
    
    # Get risk hotspots
    from services.route_safety import analyze_historical_accidents
    
    # Generate synthetic route points for the area
    from math import sin, cos, radians
    
    route_points = []
    for i in range(8):  # 8 points around the center
        angle = radians(i * 45)  # 45 degrees apart
        # Calculate points on a circle around the center
        point_lat = lat + (radius / 111) * sin(angle)  # 111 km per degree of latitude
        point_lng = lng + (radius / (111 * cos(radians(lat)))) * cos(angle)  # Adjust for longitude
        
        route_points.append({
            'lat': point_lat,
            'lng': point_lng
        })
    
    # Add center point
    route_points.append({
        'lat': lat,
        'lng': lng
    })
    
    # Get accident hotspots
    accident_hotspots = analyze_historical_accidents(route_points)
    
    return jsonify({
        "hotspots": accident_hotspots
    }), 200
