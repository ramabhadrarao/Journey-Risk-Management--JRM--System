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
    vehicles = Vehicle.get_by_user(current_user_id)
    
    # Get latest telemetry for each vehicle
    latest_telemetry = {}
    for vehicle in vehicles:
        telemetry = Telemetry.get_latest_by_vehicle(vehicle['_id'])
        if telemetry:
            latest_telemetry[str(vehicle['_id'])] = telemetry
    
    # Count risk points by type
    risk_points_by_type = defaultdict(int)
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
    vehicles = Vehicle.get_by_user(current_user_id)
    
    # Prepare response data
    vehicle_analysis = []
    
    for vehicle in vehicles:
        # Get routes for this vehicle
        routes = list(db.routes.find({
            'user_id': ObjectId(current_user_id),
            'vehicle_id': vehicle['_id'],
            'status': 'completed'
        }).sort('created_at', -1))
        
        # Get telemetry data
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
    routes = []
    for route_id in route_ids:
        route = Route.get_by_id(route_id)
        
        if not route:
            continue
        
        # Check if user owns the route (unless admin)
        user = db.users.find_one({'_id': ObjectId(current_user_id)})
        if str(route['user_id']) != current_user_id and user.get('role') != 'admin':
            continue
        
        # Get risk data
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
    active_routes = list(db.routes.find({
        'user_id': ObjectId(current_user_id),
        'last_updated': {'$gte': one_hour_ago}
    }).sort('last_updated', -1))
    
    # Get current weather alerts
    from services.weather_service import get_current_weather_alerts
    weather_alerts = get_current_weather_alerts(current_user_id)
    
    # Get vehicle status updates
    vehicle_updates = []
    vehicles = Vehicle.get_by_user(current_user_id)
    
    for vehicle in vehicles:
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

# Helper function for risk assessment
def assess_risk_points(risk_data):
    """Assess risk points and return summary"""
    if not risk_data:
        return {
            'total_risks': 0,
            'high_risks': 0,
            'medium_risks': 0,
            'low_risks': 0,
            'risk_categories': {}
        }
    
    high_risks = 0
    medium_risks = 0
    low_risks = 0
    risk_categories = {
        'accident': {'high': 0, 'medium': 0, 'low': 0},
        'weather': {'high': 0, 'medium': 0, 'low': 0},
        'elevation': {'high': 0, 'medium': 0, 'low': 0},
        'blind_spot': {'high': 0, 'medium': 0, 'low': 0},
        'network': {'high': 0, 'medium': 0, 'low': 0}
    }
    
    # Count accident risks
    for risk in risk_data.get('accident_risks', []):
        level = risk.get('risk_level', '').lower()
        if level in ['high', 'medium', 'low']:
            risk_categories['accident'][level] += 1
            if level == 'high':
                high_risks += 1
            elif level == 'medium':
                medium_risks += 1
            else:
                low_risks += 1
    
    # Count weather hazards
    for risk in risk_data.get('weather_hazards', []):
        level = risk.get('risk_level', '').lower()
        if level in ['high', 'medium', 'low']:
            risk_categories['weather'][level] += 1
            if level == 'high':
                high_risks += 1
            elif level == 'medium':
                medium_risks += 1
            else:
                low_risks += 1
    
    # Count elevation risks
    for risk in risk_data.get('elevation_risks', []):
        level = risk.get('risk_level', '').lower()
        if level in ['high', 'medium', 'low']:
            risk_categories['elevation'][level] += 1
            if level == 'high':
                high_risks += 1
            elif level == 'medium':
                medium_risks += 1
            else:
                low_risks += 1
    
    # Count blind spots
    for risk in risk_data.get('blind_spots', []):
        level = risk.get('risk_level', '').lower()
        if level in ['high', 'medium', 'low']:
            risk_categories['blind_spot'][level] += 1
            if level == 'high':
                high_risks += 1
            elif level == 'medium':
                medium_risks += 1
            else:
                low_risks += 1
    
    # Count network issues
    for risk in risk_data.get('network_coverage', []):
        level = risk.get('risk_level', '').lower()
        if level in ['high', 'medium', 'low']:
            risk_categories['network'][level] += 1
            if level == 'high':
                high_risks += 1
            elif level == 'medium':
                medium_risks += 1
            else:
                low_risks += 1
    
    total_risks = high_risks + medium_risks + low_risks
    
    return {
        'total_risks': total_risks,
        'high_risks': high_risks,
        'medium_risks': medium_risks,
        'low_risks': low_risks,
        'risk_categories': risk_categories
    }