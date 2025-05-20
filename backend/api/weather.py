from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.weather_service import get_weather_data, get_weather_hazards

weather_bp = Blueprint('weather', __name__)

@weather_bp.route('/forecast', methods=['GET'])
def get_forecast():
    """Get weather forecast for a location"""
    # Extract query parameters
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    
    if not lat or not lng:
        return jsonify({"error": "Missing lat or lng parameters"}), 400
    
    try:
        lat = float(lat)
        lng = float(lng)
    except ValueError:
        return jsonify({"error": "Invalid parameter values"}), 400
    
    # Get weather data
    weather = get_weather_data([{'lat': lat, 'lng': lng}])
    
    if not weather:
        return jsonify({"error": "Failed to get weather data"}), 500
    
    return jsonify({
        "location": {
            "lat": lat,
            "lng": lng
        },
        "weather": weather[0]
    }), 200

@weather_bp.route('/hazards', methods=['POST'])
@jwt_required()
def analyze_weather_hazards():
    """Analyze weather hazards for a route"""
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400
    
    data = request.get_json()
    
    # Validate route points
    if 'route_points' not in data or not isinstance(data['route_points'], list):
        return jsonify({"error": "Missing or invalid route_points"}), 400
    
    route_points = data['route_points']
    
    for point in route_points:
        if 'lat' not in point or 'lng' not in point:
            return jsonify({"error": "Invalid route point format"}), 400
    
    # Get weather hazards
    hazards = get_weather_hazards(route_points)
    
    return jsonify({
        "hazards": hazards
    }), 200

@weather_bp.route('/alerts', methods=['GET'])
@jwt_required()
def get_weather_alerts():
    """Get active weather alerts for user's routes"""
    current_user_id = get_jwt_identity()
    
    # Get alerts from service
    from services.weather_service import get_current_weather_alerts
    alerts = get_current_weather_alerts(current_user_id)
    
    return jsonify({
        "alerts": alerts
    }), 200
