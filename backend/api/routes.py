# backend/api/routes.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.route import Route
from models.risk_data import RiskData
from services.google_maps import get_route_details
from services.accident_prediction import predict_accident_risks
from services.weather_service import get_weather_hazards
from services.route_safety import analyze_route_safety
from services.eta_optimizer import optimize_eta
import threading
import json
from bson import ObjectId, json_util

routes_bp = Blueprint('routes', __name__)

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

def json_response(data):
    return json.loads(json_util.dumps(data))

@routes_bp.route('/', methods=['POST'])
@jwt_required()
def create_route():
    """Create a new route"""
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400
    
    data = request.get_json()
    current_user_id = get_jwt_identity()
    
    # Validate required fields
    required_fields = ['origin', 'destination']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing {field} field"}), 400
    
    # Validate origin and destination
    for location in ['origin', 'destination']:
        if 'address' not in data[location]:
            return jsonify({"error": f"Missing address in {location}"}), 400
    
    # Create route
    route = Route.create(
        user_id=current_user_id,
        origin=data['origin'],
        destination=data['destination'],
        vehicle_id=data.get('vehicle_id'),
        name=data.get('name')
    )
    
    # Create risk data entry
    risk_data = RiskData.create(route['route_id'])
    
    # Process route in background
    threading.Thread(target=process_route, args=(route['route_id'],)).start()
    
    return jsonify({
        "message": "Route created successfully, processing started",
        "route": json_response(route)
    }), 201

def process_route(route_id):
    """Process a route to get details and risks"""
    try:
        # Get route
        route = Route.get_by_id(route_id)
        if not route:
            current_app.logger.error(f"Route not found: {route_id}")
            return
        
        # Update status
        Route.update_status(route_id, 'processing')
        
        # Get route details from Google Maps
        route_details = get_route_details(
            route['origin']['address'],
            route['destination']['address']
        )
        
        # Update route with details
        Route.update_route_details(route_id, {
            'polyline': route_details['polyline'],
            'distance': route_details['distance'],
            'duration': route_details['duration'],
            'waypoints': route_details['waypoints']
        })
        
        # Get vehicle details if provided
        vehicle = None
        if route.get('vehicle_id'):
            from models.vehicle import Vehicle
            vehicle = Vehicle.get_by_id(route['vehicle_id'])
        
        # Analyze risks
        route_points = route_details['waypoints']
        
        # Get accident risks
        accident_risks = predict_accident_risks(route_points)
        RiskData.update(route_id, {'accident_risks': accident_risks})
        
        # Get weather hazards
        weather_hazards = get_weather_hazards(route_points)
        RiskData.update(route_id, {'weather_hazards': weather_hazards})
        
        # Analyze route safety (elevation, sharp turns, etc.)
        safety_data = analyze_route_safety(route_points)
        RiskData.update(route_id, {
            'elevation_risks': safety_data['elevation_risks'],
            'blind_spots': safety_data['blind_spots'],
            'network_coverage': safety_data['network_coverage'],
            'eco_sensitive_zones': safety_data['eco_sensitive_zones']
        })
        
        # Get nearby facilities
        nearby_facilities = get_nearby_facilities(route_points)
        RiskData.update(route_id, {'nearby_facilities': nearby_facilities})
        
        # Calculate risk score
        risk_score, risk_level = calculate_overall_risk(route_id)
        RiskData.update_risk_score(route_id, risk_score, risk_level)
        
        # Optimize ETA
        optimized_duration = optimize_eta(
            route_points, 
            vehicle_type=vehicle['type'] if vehicle else 'car',
            weather_data=weather_hazards
        )
        
        # Update route with final details
        Route.update_route_details(route_id, {
            'optimized_duration': optimized_duration,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'status': 'completed'
        })
        
        # Emit real-time update via Socket.IO
        from app import socketio
        socketio.emit(f'route_update_{route_id}', {
            'status': 'completed',
            'risk_score': risk_score,
            'risk_level': risk_level
        })
        
    except Exception as e:
        current_app.logger.error(f"Error processing route {route_id}: {str(e)}")
        Route.update_status(route_id, 'failed')
        
        # Emit error via Socket.IO
        from app import socketio
        socketio.emit(f'route_update_{route_id}', {
            'status': 'failed',
            'error': str(e)
        })

def get_nearby_facilities(route_points):
    """Get nearby facilities for route points"""
    from services.google_maps import get_nearby_places
    
    # Sample route points to reduce API calls
    sampled_points = [route_points[i] for i in range(0, len(route_points), max(1, len(route_points) // 10))]
    
    facilities = {
        'hospitals': [],
        'police_stations': [],
        'fuel_stations': [],
        'rest_areas': [],
        'repair_shops': []
    }
    
    # Map facility types to Google Places types
    type_mapping = {
        'hospitals': 'hospital',
        'police_stations': 'police',
        'fuel_stations': 'gas_station',
        'rest_areas': 'restaurant',
        'repair_shops': 'car_repair'
    }
    
    # Set of seen place IDs to avoid duplicates
    seen_place_ids = set()
    
    # Search for facilities at different distance ranges
    distance_ranges = [1000, 5000, 10000]  # meters
    
    for point in sampled_points:
        for facility_type, place_type in type_mapping.items():
            for distance in distance_ranges:
                places = get_nearby_places(
                    point['lat'], 
                    point['lng'], 
                    place_type, 
                    radius=distance
                )
                
                for place in places:
                    if place['place_id'] not in seen_place_ids:
                        seen_place_ids.add(place['place_id'])
                        
                        facilities[facility_type].append({
                            'name': place['name'],
                            'vicinity': place.get('vicinity', ''),
                            'location': {
                                'lat': place['geometry']['location']['lat'],
                                'lng': place['geometry']['location']['lng']
                            },
                            'distance': place['distance'],
                            'place_id': place['place_id']
                        })
    
    return facilities

def calculate_overall_risk(route_id):
    """Calculate overall risk score and level for a route"""
    from config import RISK_THRESHOLDS
    
    risk_data = RiskData.get_by_route_id(route_id)
    if not risk_data:
        return 0, 'unknown'
    
    # Count risks by category and severity
    risk_counts = {
        'high': 0,
        'medium': 0,
        'low': 0
    }
    
    # Count accident risks
    for risk in risk_data.get('accident_risks', []):
        risk_level = risk.get('risk_level', '').lower()
        if risk_level in risk_counts:
            risk_counts[risk_level] += 1
    
    # Count weather hazards
    for hazard in risk_data.get('weather_hazards', []):
        risk_level = hazard.get('risk_level', '').lower()
        if risk_level in risk_counts:
            risk_counts[risk_level] += 1
    
    # Count elevation risks
    for risk in risk_data.get('elevation_risks', []):
        risk_level = risk.get('risk_level', '').lower()
        if risk_level in risk_counts:
            risk_counts[risk_level] += 1
    
    # Count blind spots
    for spot in risk_data.get('blind_spots', []):
        risk_level = spot.get('risk_level', '').lower()
        if risk_level in risk_counts:
            risk_counts[risk_level] += 1
    
    # Count network coverage issues
    for issue in risk_data.get('network_coverage', []):
        risk_level = issue.get('risk_level', '').lower()
        if risk_level in risk_counts:
            risk_counts[risk_level] += 1
    
    # Calculate weighted risk score
    total_risks = sum(risk_counts.values())
    if total_risks == 0:
        return 0, 'low'
    
    # Weight: high=5, medium=2, low=1
    weighted_score = (
        5 * risk_counts['high'] + 
        2 * risk_counts['medium'] + 
        1 * risk_counts['low']
    ) / total_risks
    
    # Normalize to 0-10 scale
    normalized_score = min(10, (weighted_score / 5) * 10)
    
    # Determine risk level
    if normalized_score >= RISK_THRESHOLDS['route_safety']['high']:
        risk_level = 'high'
    elif normalized_score >= RISK_THRESHOLDS['route_safety']['medium']:
        risk_level = 'medium'
    else:
        risk_level = 'low'
    
    return round(normalized_score, 1), risk_level

@routes_bp.route('/', methods=['GET'])
@jwt_required()
def get_routes():
    """Get user routes"""
    current_user_id = get_jwt_identity()
    
    # Pagination parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    # Calculate skip
    skip = (page - 1) * per_page
    
    # Get routes
    routes = Route.get_by_user(current_user_id, limit=per_page, skip=skip)
    
    # Count total routes
    total_routes = db.routes.count_documents({'user_id': ObjectId(current_user_id)})
    
    return jsonify({
        "routes": json_response(routes),
        "total": total_routes,
        "page": page,
        "per_page": per_page,
        "total_pages": (total_routes + per_page - 1) // per_page
    }), 200

@routes_bp.route('/<route_id>', methods=['GET'])
@jwt_required()
def get_route(route_id):
    """Get route by ID"""
    current_user_id = get_jwt_identity()
    
    # Get route
    route = Route.get_by_id(route_id)
    
    if not route:
        return jsonify({"error": "Route not found"}), 404
    
    # Check if user owns the route (unless admin)
    user = db.users.find_one({'_id': ObjectId(current_user_id)})
    if str(route['user_id']) != current_user_id and user.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    # Get risk data
    risk_data = RiskData.get_by_route_id(route_id)
    
    return jsonify({
        "route": json_response(route),
        "risk_data": json_response(risk_data)
    }), 200

@routes_bp.route('/<route_id>', methods=['DELETE'])
@jwt_required()
def delete_route(route_id):
    """Delete route"""
    current_user_id = get_jwt_identity()
    
    # Get route
    route = Route.get_by_id(route_id)
    
    if not route:
        return jsonify({"error": "Route not found"}), 404
    
    # Check if user owns the route (unless admin)
    user = db.users.find_one({'_id': ObjectId(current_user_id)})
    if str(route['user_id']) != current_user_id and user.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    # Delete route and risk data
    Route.delete(route_id)
    db.risk_data.delete_one({'route_id': route_id})
    
    return jsonify({
        "message": "Route deleted successfully"
    }), 200

@routes_bp.route('/<route_id>/regenerate', methods=['POST'])
@jwt_required()
def regenerate_route(route_id):
    """Regenerate route analysis"""
    current_user_id = get_jwt_identity()
    
    # Get route
    route = Route.get_by_id(route_id)
    
    if not route:
        return jsonify({"error": "Route not found"}), 404
    
    # Check if user owns the route (unless admin)
    user = db.users.find_one({'_id': ObjectId(current_user_id)})
    if str(route['user_id']) != current_user_id and user.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    # Update status
    Route.update_status(route_id, 'processing')
    
    # Process route in background
    threading.Thread(target=process_route, args=(route_id,)).start()
    
    return jsonify({
        "message": "Route regeneration started"
    }), 200