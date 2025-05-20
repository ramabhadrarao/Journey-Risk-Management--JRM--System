#!/bin/bash
# restore_api_files.sh - Restore original API files from the codebase

echo "Restoring original API files from the codebase..."

# Make sure the api directory exists
mkdir -p api

# Create risk_analysis.py (using a minimal implementation since we don't have the original)
echo "Creating api/risk_analysis.py..."
cat > api/risk_analysis.py << 'EOL'
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
EOL

# Create weather.py based on the codebase
echo "Creating api/weather.py..."
cat > api/weather.py << 'EOL'
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
EOL

# Restore the original dashboard.py file from the codebase
echo "Creating api/dashboard.py from the original codebase..."
cat > api/dashboard.py << 'EOL'
# backend/api/dashboard.py (COMPLETE CODE)
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from pymongo import MongoClient
from bson import ObjectId, json_util
import json
import datetime
from collections import defaultdict

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

def json_response(data):
    return json.loads(json_util.dumps(data))

@dashboard_bp.route('/summary')
@jwt_required()
def get_dashboard_summary():
    """Get dashboard summary data for the user"""
    current_user_id = get_jwt_identity()
    
    # Get recent routes (last 30 days)
    thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    from models import db
    recent_routes = list(db.routes.find({
        'user_id': ObjectId(current_user_id),
        'created_at': {'$gte': thirty_days_ago}
    }).sort('created_at', -1))
    
    # Calculate risk distribution
    risk_distribution = {
        'high': 0,
        'medium': 0,
        'low': 0,
        'unknown': 0
    }
    
    total_distance = 0
    total_duration = 0
    
    for route in recent_routes:
        risk_level = route.get('risk_level', 'unknown').lower()
        if risk_level in risk_distribution:
            risk_distribution[risk_level] += 1
        
        # Extract numeric distance (remove 'km' and convert to float)
        if route.get('distance'):
            try:
                distance_str = route['distance'].replace('km', '').replace('mi', '').strip()
                distance = float(distance_str)
                total_distance += distance
            except (ValueError, AttributeError):
                pass
        
        # Extract numeric duration (convert HH:MM:SS to minutes)
        if route.get('duration'):
            try:
                duration_parts = route['duration'].split()
                duration_minutes = 0
                
                for i in range(0, len(duration_parts), 2):
                    value = float(duration_parts[i])
                    unit = duration_parts[i+1] if i+1 < len(duration_parts) else ''
                    
                    if 'hour' in unit:
                        duration_minutes += value * 60
                    elif 'min' in unit:
                        duration_minutes += value
                
                total_duration += duration_minutes
            except (ValueError, IndexError, AttributeError):
                pass
    
    # Get vehicles
    from models.vehicle import Vehicle
    vehicles = Vehicle.get_by_user(current_user_id)
    
    # Get latest telemetry for each vehicle
    from models.telemetry import Telemetry
    latest_telemetry = {}
    for vehicle in vehicles:
        telemetry = Telemetry.get_latest_by_vehicle(vehicle['_id'])
        if telemetry:
            latest_telemetry[str(vehicle['_id'])] = telemetry
    
    # Count risk points by type
    risk_points_by_type = defaultdict(int)
    from models.risk_data import RiskData
    for route in recent_routes:
        risk_data = RiskData.get_by_route_id(route['route_id'])
        if risk_data:
            risk_points_by_type['accident'] += len(risk_data.get('accident_risks', []))
            risk_points_by_type['weather'] += len(risk_data.get('weather_hazards', []))
            risk_points_by_type['elevation'] += len(risk_data.get('elevation_risks', []))
            risk_points_by_type['blind_spot'] += len(risk_data.get('blind_spots', []))
            risk_points_by_type['network'] += len(risk_data.get('network_coverage', []))
            risk_points_by_type['eco_zone'] += len(risk_data.get('eco_sensitive_zones', []))
    
    return jsonify({
        "summary": {
            "total_routes": len(recent_routes),
            "total_distance": round(total_distance, 1),
            "total_duration": round(total_duration / 60, 1),  # in hours
            "risk_distribution": risk_distribution,
            "total_vehicles": len(vehicles),
            "risk_points_by_type": dict(risk_points_by_type)
        },
        "recent_routes": json_response(recent_routes[:5]),
        "vehicles": json_response(vehicles),
        "latest_telemetry": json_response(latest_telemetry)
    }), 200

@dashboard_bp.route('/risk-analysis')
@jwt_required()
def get_risk_analysis():
    """Get risk analysis data for visualization"""
    current_user_id = get_jwt_identity()
    
    # Get time range from query parameters (default: last 30 days)
    days = int(request.args.get('days', 30))
    start_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    
    # Get routes in the time range
    from models import db
    routes = list(db.routes.find({
        'user_id': ObjectId(current_user_id),
        'created_at': {'$gte': start_date},
        'status': 'completed'
    }).sort('created_at', 1))
    
    # Prepare data for visualization
    
    # 1. Risk trends over time
    risk_trends = []
    for route in routes:
        if route.get('risk_score') is not None:
            risk_trends.append({
                'date': route['created_at'],
                'risk_score': route['risk_score'],
                'route_id': route['route_id'],
                'route_name': route.get('name', f"Route {route['route_id'][:8]}")
            })
    
    # 2. Risk categories distribution
    risk_categories = defaultdict(lambda: {'high': 0, 'medium': 0, 'low': 0})
    
    from models.risk_data import RiskData
    for route in routes:
        risk_data = RiskData.get_by_route_id(route['route_id'])
        if not risk_data:
            continue
        
        # Count accident risks
        for risk in risk_data.get('accident_risks', []):
            level = risk.get('risk_level', '').lower()
            if level in ['high', 'medium', 'low']:
                risk_categories['accident'][level] += 1
        
        # Count weather hazards
        for risk in risk_data.get('weather_hazards', []):
            level = risk.get('risk_level', '').lower()
            if level in ['high', 'medium', 'low']:
                risk_categories['weather'][level] += 1
        
        # Count elevation risks
        for risk in risk_data.get('elevation_risks', []):
            level = risk.get('risk_level', '').lower()
            if level in ['high', 'medium', 'low']:
                risk_categories['elevation'][level] += 1
        
        # Count blind spots
        for risk in risk_data.get('blind_spots', []):
            level = risk.get('risk_level', '').lower()
            if level in ['high', 'medium', 'low']:
                risk_categories['blind_spot'][level] += 1
        
        # Count network issues
        for risk in risk_data.get('network_coverage', []):
            level = risk.get('risk_level', '').lower()
            if level in ['high', 'medium', 'low']:
                risk_categories['network'][level] += 1
    
    # 3. Risk heatmap data (aggregate risk points by location)
    risk_heatmap = []
    
    for route in routes:
        risk_data = RiskData.get_by_route_id(route['route_id'])
        if not risk_data:
            continue
        
        # Add all risk points to heatmap
        for category in ['accident_risks', 'weather_hazards', 'elevation_risks', 
                        'blind_spots', 'network_coverage']:
            for risk in risk_data.get(category, []):
                if 'location' in risk:
                    location = risk['location']
                elif 'coordinates' in risk:
                    location = risk['coordinates']
                else:
                    continue
                
                # Convert risk level to weight
                level = risk.get('risk_level', '').lower()
                weight = 3 if level == 'high' else 2 if level == 'medium' else 1
                
                risk_heatmap.append({
                    'lat': location['lat'],
                    'lng': location['lng'],
                    'weight': weight
                })
    
    # 4. Time-of-day analysis
    time_analysis = {
        'morning': {'high': 0, 'medium': 0, 'low': 0},
        'afternoon': {'high': 0, 'medium': 0, 'low': 0},
        'evening': {'high': 0, 'medium': 0, 'low': 0},
        'night': {'high': 0, 'medium': 0, 'low': 0}
    }
    
    for route in routes:
        if not route.get('created_at') or not route.get('risk_level'):
            continue
        
        # Determine time of day
        hour = route['created_at'].hour
        if 6 <= hour < 12:
            time_period = 'morning'
        elif 12 <= hour < 17:
            time_period = 'afternoon'
        elif 17 <= hour < 22:
            time_period = 'evening'
        else:
            time_period = 'night'
        
        # Count by risk level
        level = route.get('risk_level', '').lower()
        if level in ['high', 'medium', 'low']:
            time_analysis[time_period][level] += 1
    
    # 5. Nearby facilities statistics
    facilities_stats = {
        'hospitals': {
            'under_1km': 0,
            '1km_to_5km': 0,
            'over_5km': 0
        },
        'police_stations': {
            'under_1km': 0,
            '1km_to_5km': 0,
            'over_5km': 0
        },
        'fuel_stations': {
            'under_1km': 0,
            '1km_to_5km': 0,
            'over_5km': 0
        },
        'repair_shops': {
            'under_1km': 0,
            '1km_to_5km': 0,
            'over_5km': 0
        }
    }
    
    for route in routes:
        risk_data = RiskData.get_by_route_id(route['route_id'])
        if not risk_data or 'nearby_facilities' not in risk_data:
            continue
        
        for facility_type in facilities_stats.keys():
            if facility_type not in risk_data['nearby_facilities']:
                continue
                
            for facility in risk_data['nearby_facilities'][facility_type]:
                distance = facility.get('distance', 0)
                
                if distance <= 1000:
                    facilities_stats[facility_type]['under_1km'] += 1
                elif distance <= 5000:
                    facilities_stats[facility_type]['1km_to_5km'] += 1
                else:
                    facilities_stats[facility_type]['over_5km'] += 1
    
    return jsonify({
        "risk_trends": json_response(risk_trends),
        "risk_categories": json_response(dict(risk_categories)),
        "risk_heatmap": risk_heatmap,
        "time_analysis": time_analysis,
        "facilities_stats": facilities_stats
    }), 200

@dashboard_bp.route('/vehicle-analysis')
@jwt_required()
def get_vehicle_analysis():
    """Get vehicle analysis data for visualization"""
    current_user_id = get_jwt_identity()
    
    # Get vehicles
    from models.vehicle import Vehicle
    vehicles = Vehicle.get_by_user(current_user_id)
    
    # Prepare response data
    vehicle_analysis = []
    
    for vehicle in vehicles:
        # Get routes for this vehicle
        from models import db
        routes = list(db.routes.find({
            'user_id': ObjectId(current_user_id),
            'vehicle_id': vehicle['_id'],
            'status': 'completed'
        }).sort('created_at', -1))
        
        # Get telemetry data
        from models.telemetry import Telemetry
        telemetry_data = Telemetry.get_by_vehicle(vehicle['_id'], limit=1000)
        
        # Calculate stats
        total_distance = 0
        total_duration = 0
        risk_levels = {'high': 0, 'medium': 0, 'low': 0}
        
        for route in routes:
            # Extract distance
            if route.get('distance'):
                try:
                    distance_str = route['distance'].replace('km', '').replace('mi', '').strip()
                    distance = float(distance_str)
                    total_distance += distance
                except (ValueError, AttributeError):
                    pass
            
            # Extract duration
            if route.get('duration'):
                try:
                    duration_parts = route['duration'].split()
                    duration_minutes = 0
                    
                    for i in range(0, len(duration_parts), 2):
                        value = float(duration_parts[i])
                        unit = duration_parts[i+1] if i+1 < len(duration_parts) else ''
                        
                        if 'hour' in unit:
                            duration_minutes += value * 60
                        elif 'min' in unit:
                            duration_minutes += value
                    
                    total_duration += duration_minutes
                except (ValueError, IndexError, AttributeError):
                    pass
            
            # Count risk levels
            level = route.get('risk_level', '').lower()
            if level in risk_levels:
                risk_levels[level] += 1
        
        # Prepare fuel efficiency analysis
        fuel_data = []
        engine_temp_data = []
        
        for record in telemetry_data:
            if 'timestamp' in record and 'fuel_level' in record:
                fuel_data.append({
                    'timestamp': record['timestamp'],
                    'fuel_level': record['fuel_level']
                })
            
            if 'timestamp' in record and 'engine_temp' in record:
                engine_temp_data.append({
                    'timestamp': record['timestamp'],
                    'engine_temp': record['engine_temp']
                })
        
        # Predict breakdown probability
        from services.breakdown_predictor import predict_breakdown_probability
        breakdown_probability = 0
        
        if telemetry_data:
            latest_telemetry = telemetry_data[0]
            maintenance_history = vehicle.get('maintenance', {}).get('history', [])
            
            breakdown_probability = predict_breakdown_probability(
                vehicle, latest_telemetry, maintenance_history
            )
        
        # Prepare response for this vehicle
        vehicle_analysis.append({
            'vehicle': json_response(vehicle),
            'stats': {
                'total_routes': len(routes),
                'total_distance': round(total_distance, 1),
                'total_duration': round(total_duration / 60, 1),  # in hours
                'risk_levels': risk_levels,
                'breakdown_probability': round(breakdown_probability * 100, 1)  # as percentage
            },
            'telemetry': {
                'fuel_data': json_response(fuel_data[-20:]),  # last 20 records
                'engine_temp_data': json_response(engine_temp_data[-20:])  # last 20 records
            },
            'recent_routes': json_response(routes[:5])
        })
    
    return jsonify({
        "vehicle_analysis": vehicle_analysis
    }), 200

@dashboard_bp.route('/route-comparison', methods=['POST'])
@jwt_required()
def compare_routes():
    """Compare multiple routes"""
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400
    
    data = request.get_json()
    current_user_id = get_jwt_identity()
    
    # Validate required fields
    if 'route_ids' not in data or not isinstance(data['route_ids'], list):
        return jsonify({"error": "Missing or invalid route_ids"}), 400
    
    route_ids = data['route_ids']
    
    # Get routes
    from models.route import Route
    routes = []
    for route_id in route_ids:
        route = Route.get_by_id(route_id)
        
        if not route:
            continue
        
        # Check if user owns the route (unless admin)
        from models import db
        user = db.users.find_one({'_id': ObjectId(current_user_id)})
        if str(route['user_id']) != current_user_id and user.get('role') != 'admin':
            continue
        
        # Get risk data
        from models.risk_data import RiskData
        risk_data = RiskData.get_by_route_id(route_id)
        
        routes.append({
            'route': route,
            'risk_data': risk_data
        })
    
    # Prepare comparison data
    comparison = []
    
    for route_data in routes:
        route = route_data['route']
        risk_data = route_data['risk_data']
        
        # Count risks by category
        risk_counts = {
            'accident': len(risk_data.get('accident_risks', [])),
            'weather': len(risk_data.get('weather_hazards', [])),
            'elevation': len(risk_data.get('elevation_risks', [])),
            'blind_spot': len(risk_data.get('blind_spots', [])),
            'network': len(risk_data.get('network_coverage', [])),
            'eco_zone': len(risk_data.get('eco_sensitive_zones', []))
        }
        
        # Count nearby facilities
        facility_counts = {}
        for facility_type, facilities in risk_data.get('nearby_facilities', {}).items():
            facility_counts[facility_type] = len(facilities)
        
        # Extract distance and duration
        distance = 0
        duration = 0
        
        if route.get('distance'):
            try:
                distance_str = route['distance'].replace('km', '').replace('mi', '').strip()
                distance = float(distance_str)
            except (ValueError, AttributeError):
                pass
        
        if route.get('duration'):
            try:
                duration_parts = route['duration'].split()
                duration_minutes = 0
                
                for i in range(0, len(duration_parts), 2):
                    value = float(duration_parts[i])
                    unit = duration_parts[i+1] if i+1 < len(duration_parts) else ''
                    
                    if 'hour' in unit:
                        duration_minutes += value * 60
                    elif 'min' in unit:
                        duration_minutes += value
                
                duration = duration_minutes
            except (ValueError, IndexError, AttributeError):
                pass
        
        # Prepare comparison item
        comparison.append({
            'route_id': route['route_id'],
            'name': route.get('name', f"Route {route['route_id'][:8]}"),
            'created_at': route['created_at'],
            'distance': distance,
            'duration': duration,
            'optimized_duration': route.get('optimized_duration'),
            'risk_score': route.get('risk_score', 0),
            'risk_level': route.get('risk_level', 'unknown'),
            'risk_counts': risk_counts,
            'facility_counts': facility_counts,
            'origin': route['origin']['address'],
            'destination': route['destination']['address']
        })
    
    return jsonify({
        "comparison": json_response(comparison)
    }), 200

@dashboard_bp.route('/real-time-updates')
@jwt_required()
def get_real_time_updates():
    """Get current real-time updates for dashboard"""
    current_user_id = get_jwt_identity()
    
    # Get active routes (processed in the last hour)
    one_hour_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    from models import db
    active_routes = list(db.routes.find({
        'user_id': ObjectId(current_user_id),
        'last_updated': {'$gte': one_hour_ago}
    }).sort('last_updated', -1))
    
    # Get current weather alerts
    from services.weather_service import get_current_weather_alerts
    weather_alerts = get_current_weather_alerts(current_user_id)
    
    # Get vehicle status updates
    vehicle_updates = []
    from models.vehicle import Vehicle
    vehicles = Vehicle.get_by_user(current_user_id)
    
    for vehicle in vehicles:
        from models.telemetry import Telemetry
        latest_telemetry = Telemetry.get_latest_by_vehicle(vehicle['_id'])
        if latest_telemetry and 'timestamp' in latest_telemetry:
            # Only include if telemetry is recent (within last hour)
            if latest_telemetry['timestamp'] >= one_hour_ago:
                vehicle_updates.append({
                    'vehicle_id': str(vehicle['_id']),
                    'vehicle_name': vehicle.get('name', 'Vehicle'),
                    'telemetry': json_response(latest_telemetry)
                })
    
    return jsonify({
        "active_routes": json_response(active_routes),
        "weather_alerts": weather_alerts,
        "vehicle_updates": vehicle_updates
    }), 200
EOL

# Create vehicles.py based on the codebase
echo "Creating api/vehicles.py..."
cat > api/vehicles.py << 'EOL'
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
EOL

# Update the app.py file to work with the original API modules
echo "Updating app.py to work with original API modules..."
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

# Import and register blueprints
from api.auth import auth_bp, apply_rate_limits

# Register auth blueprint and apply rate limits
app.register_blueprint(auth_bp, url_prefix='/api/auth')
apply_rate_limits(app)

# Import and register other blueprints if they exist
try:
    from api.routes import routes_bp
    app.register_blueprint(routes_bp, url_prefix='/api/routes')
except ImportError:
    app.logger.warning("routes_bp blueprint not available")

try:
    from api.risk_analysis import risk_bp
    app.register_blueprint(risk_bp, url_prefix='/api/risk')
except ImportError:
    app.logger.warning("risk_bp blueprint not available")

try:
    from api.weather import weather_bp
    app.register_blueprint(weather_bp, url_prefix='/api/weather')
except ImportError:
    app.logger.warning("weather_bp blueprint not available")

try:
    from api.vehicles import vehicles_bp
    app.register_blueprint(vehicles_bp, url_prefix='/api/vehicles')
except ImportError:
    app.logger.warning("vehicles_bp blueprint not available")

try:
    from api.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
except ImportError:
    app.logger.warning("dashboard_bp blueprint not available")

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

echo "Restored original API files from the codebase."
echo "Try running the application with: python run.py"