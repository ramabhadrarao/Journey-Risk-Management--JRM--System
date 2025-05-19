# backend/services/route_safety.py (COMPLETE CODE)
import os
import numpy as np
import pandas as pd
import pickle
import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from flask import current_app
from config import MODEL_FOLDER
import math

def analyze_route_safety(route_points):
    """
    Analyze route safety features like elevation, sharp turns, etc.
    
    Args:
        route_points: List of dictionaries with lat, lng coordinates
        
    Returns:
        Dictionary with different safety analyses
    """
    if not route_points or len(route_points) < 3:
        return {
            'elevation_risks': [],
            'blind_spots': [],
            'network_coverage': [],
            'eco_sensitive_zones': []
        }
    
    # Analyze elevation
    elevation_risks = analyze_elevation_risks(route_points)
    
    # Analyze blind spots
    blind_spots = analyze_blind_spots(route_points)
    
    # Analyze network coverage
    network_coverage = analyze_network_coverage(route_points)
    
    # Analyze eco-sensitive zones
    eco_sensitive_zones = analyze_eco_sensitive_zones(route_points)
    
    return {
        'elevation_risks': elevation_risks,
        'blind_spots': blind_spots,
        'network_coverage': network_coverage,
        'eco_sensitive_zones': eco_sensitive_zones
    }

def analyze_elevation_risks(route_points):
    """Analyze elevation changes and identify risks"""
    # Get elevation data
    from services.google_maps import get_elevation_data
    elevation_data = get_elevation_data(route_points)
    
    elevation_risks = []
    
    # Analyze elevation changes
    for i in range(1, len(elevation_data)):
        prev_point = elevation_data[i-1]
        curr_point = elevation_data[i]
        
        # Calculate distance between points
        distance = calculate_distance(
            prev_point['lat'], prev_point['lng'],
            curr_point['lat'], curr_point['lng']
        )
        
        # Skip if distance is too small
        if distance < 0.01:  # 10 meters
            continue
        
        # Calculate elevation change
        elevation_change = curr_point['elevation'] - prev_point['elevation']
        
        # Calculate gradient (in percentage)
        if distance > 0:
            gradient = (elevation_change / (distance * 1000)) * 100
        else:
            gradient = 0
        
        # Identify significant gradients
        if abs(gradient) >= 7:
            risk_type = 'Ascent' if gradient > 0 else 'Descent'
            
            # Determine risk level based on gradient
            if abs(gradient) >= 15:
                risk_level = 'High'
            elif abs(gradient) >= 10:
                risk_level = 'Medium'
            else:
                risk_level = 'Low'
            
            elevation_risks.append({
                'location': {
                    'lat': curr_point['lat'],
                    'lng': curr_point['lng']
                },
                'risk_type': risk_type,
                'risk_level': risk_level,
                'gradient': round(gradient, 1),
                'elevation': round(curr_point['elevation'], 1),
                'distance': round(distance * 1000, 0)  # meters
            })
    
    return elevation_risks

def analyze_blind_spots(route_points):
    """Analyze route for potential blind spots"""
    # Load blind spot model
    model_path = os.path.join(MODEL_FOLDER, 'route_safety', 'blind_spot_model.pkl')
    
    try:
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
    except (FileNotFoundError, EOFError):
        # If model doesn't exist, train a new one
        model = train_blind_spot_model()
    
    blind_spots = []
    
    # Sample route points (every 20th point)
    sampled_points = [route_points[i] for i in range(0, len(route_points), 20)]
    
    # Ensure we have critical points (turns)
    turns = identify_sharp_turns(route_points)
    for turn in turns:
        if turn['angle'] < 135:  # Significant turn
            sampled_points.append(turn['location'])
    
    # Remove duplicates
    sampled_points = [dict(t) for t in {tuple(sorted(d.items())) for d in sampled_points}]
    
    # Get road geometry for sampled points
    from services.google_maps import get_road_geometry
    road_geometry = get_road_geometry(sampled_points)
    
    # Get elevation data
    from services.google_maps import get_elevation_data
    elevation_data = get_elevation_data(sampled_points)
    
    # Analyze each point
    for i, point in enumerate(sampled_points):
        # Find corresponding geometry and elevation
        geometry = next((g for g in road_geometry if 
                       g['location']['lat'] == point['lat'] and 
                       g['location']['lng'] == point['lng']), None)
        
        elevation = next((e for e in elevation_data if 
                        e['lat'] == point['lat'] and 
                        e['lng'] == point['lng']), None)
        
        if not geometry or not elevation:
            continue
        
        # Prepare features
        features = {
            'road_width': geometry.get('road_width', 0),
            'curvature': geometry.get('curvature', 0),
            'gradient': geometry.get('gradient', 0),
            'visibility': geometry.get('visibility', 10),
            'is_intersection': 1 if geometry.get('is_intersection', False) else 0,
            'elevation': elevation.get('elevation', 0)
        }
        
        # Convert to DataFrame
        df = pd.DataFrame([features])
        
        # Make prediction
        probability = model.predict_proba(df)[0][1]
        
        # Add to blind spots if probability is high enough
        if probability >= 0.6:
            risk_level = 'High' if probability >= 0.8 else 'Medium'
            
            blind_spots.append({
                'location': {
                    'lat': point['lat'],
                    'lng': point['lng']
                },
                'risk_level': risk_level,
                'probability': round(probability, 3),
                'features': {
                    'road_width': features['road_width'],
                    'curvature': features['curvature'],
                    'gradient': features['gradient'],
                    'visibility': features['visibility'],
                    'is_intersection': features['is_intersection'] == 1
                }
            })
    
    return blind_spots

def analyze_network_coverage(route_points):
    """Analyze network coverage along the route"""
    network_coverage = []
    
    # Sample route points (every 30th point)
    sampled_points = [route_points[i] for i in range(0, len(route_points), 30)]
    
    # Get network coverage data
    from services.network_service import get_network_data
    coverage_data = get_network_data(sampled_points)
    
    # Analyze each point
    for coverage in coverage_data:
        signal_strength = coverage.get('signal_strength', 0)
        
        # Determine risk level
        if signal_strength < 20:
            risk_level = 'High'
        elif signal_strength < 50:
            risk_level = 'Medium'
        else:
            risk_level = 'Low'
        
        # Only add points with significant risk
        if signal_strength < 70:
            network_coverage.append({
                'location': coverage['location'],
                'risk_level': risk_level,
                'signal_strength': signal_strength,
                'network_type': coverage.get('network_type', 'Unknown'),
                'provider': coverage.get('provider', 'Unknown')
            })
    
    return network_coverage

def analyze_eco_sensitive_zones(route_points):
    """Identify eco-sensitive zones along the route"""
    eco_sensitive_zones = []
    
    # Sample route points (every 50th point)
    sampled_points = [route_points[i] for i in range(0, len(route_points), 50)]
    
    # Get eco-sensitive zone data
    from services.environmental_service import get_eco_zones
    zones = get_eco_zones(sampled_points)
    
    for zone in zones:
        eco_sensitive_zones.append({
            'location': zone['location'],
            'zone_name': zone['name'],
            'zone_type': zone['type'],
            'restrictions': zone['restrictions']
        })
    
    return eco_sensitive_zones

def identify_sharp_turns(route_points):
    """Identify sharp turns in the route"""
    turns = []
    
    # Need at least 3 points to identify turns
    if len(route_points) < 3:
        return turns
    
    for i in range(1, len(route_points) - 1):
        prev_point = route_points[i-1]
        curr_point = route_points[i]
        next_point = route_points[i+1]
        
        # Calculate vectors
        vector1 = (
            curr_point['lat'] - prev_point['lat'],
            curr_point['lng'] - prev_point['lng']
        )
        
        vector2 = (
            next_point['lat'] - curr_point['lat'],
            next_point['lng'] - curr_point['lng']
        )
        
        # Calculate dot product
        dot_product = vector1[0] * vector2[0] + vector1[1] * vector2[1]
        
        # Calculate magnitudes
        mag1 = math.sqrt(vector1[0]**2 + vector1[1]**2)
        mag2 = math.sqrt(vector2[0]**2 + vector2[1]**2)
        
        # Calculate angle in degrees
        if mag1 > 0 and mag2 > 0:
            cos_angle = dot_product / (mag1 * mag2)
            # Clamp to valid range for acos
            cos_angle = max(-1, min(1, cos_angle))
            angle_rad = math.acos(cos_angle)
            angle_deg = math.degrees(angle_rad)
        else:
            angle_deg = 0
        
        # Identify sharp turns (angles significantly different from 180 degrees)
        if angle_deg < 150:
            turns.append({
                'location': {
                    'lat': curr_point['lat'],
                    'lng': curr_point['lng']
                },
                'angle': angle_deg
            })
    
    return turns

def train_blind_spot_model():
    """Train a new blind spot prediction model"""
    current_app.logger.info("Training new blind spot prediction model")
    
    # In a real-world scenario, you would load historical data about blind spots
    # and train a model. For demonstration, create a synthetic model.
    
    # Create synthetic training data
    np.random.seed(42)
    n_samples = 2000
    
    # Generate features
    X = pd.DataFrame({
        'road_width': np.random.normal(7, 2, n_samples).clip(3, 15),
        'curvature': np.random.exponential(0.5, n_samples),
        'gradient': np.random.normal(0, 5, n_samples),
        'visibility': np.random.normal(8, 4, n_samples).clip(0, 20),
        'is_intersection': np.random.binomial(1, 0.2, n_samples),
        'elevation': np.random.normal(200, 100, n_samples)
    })
    
    # Generate target variable (blind spot present)
    # Higher probability for certain conditions
    blind_spot_prob = (
        0.05 +  # base rate
        0.2 * (X['road_width'] < 5).astype(int) +          # narrow roads
        0.3 * (X['curvature'] > 1).astype(int) +           # high curvature
        0.15 * (abs(X['gradient']) > 10).astype(int) +     # steep gradients
        0.4 * (X['visibility'] < 3).astype(int) +          # low visibility
        0.2 * X['is_intersection'] +                       # intersections
        0.1 * ((X['elevation'] > 300) & 
               (X['curvature'] > 0.5)).astype(int)         # elevated curves
    ).clip(0, 1)
    
    y = np.random.binomial(1, blind_spot_prob)
    
    # Train model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # Save model
    os.makedirs(os.path.join(MODEL_FOLDER, 'route_safety'), exist_ok=True)
    model_path = os.path.join(MODEL_FOLDER, 'route_safety', 'blind_spot_model.pkl')
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    return model

def update_route_safety():
    """Update route safety models"""
    current_app.logger.info("Updating route safety models")
    
    # In a real-world scenario, you would fetch new data about road safety
    # and update the models. For demonstration, just train a new model.
    train_blind_spot_model()

def analyze_route_geometry(route_points):
    """Analyze route geometry for potential risk factors"""
    if len(route_points) < 3:
        return {
            'sharp_turns': [],
            'dangerous_intersections': []
        }
    
    sharp_turns = []
    dangerous_intersections = []
    
    # Identify sharp turns
    for i in range(1, len(route_points) - 1):
        turn = calculate_turn_angle(
            route_points[i-1],
            route_points[i],
            route_points[i+1]
        )
        
        # Angles less than 135 degrees are considered sharp
        if turn['angle'] < 135:
            risk_level = 'High' if turn['angle'] < 90 else 'Medium'
            sharp_turns.append({
                'location': turn['location'],
                'angle': turn['angle'],
                'risk_level': risk_level
            })
    
    # Get road geometry for additional analysis
    road_geometry = get_road_geometry(route_points)
    
    # Identify dangerous intersections
    for geometry in road_geometry:
        if geometry.get('is_intersection', False):
            # Intersections with poor visibility or high traffic are higher risk
            visibility = geometry.get('visibility', 10)
            traffic = geometry.get('traffic_congestion', 0)
            
            if visibility < 5 or traffic > 2:
                risk_level = 'High' if visibility < 3 or traffic > 3 else 'Medium'
                dangerous_intersections.append({
                    'location': geometry['location'],
                    'visibility': visibility,
                    'traffic': traffic,
                    'risk_level': risk_level
                })
    
    return {
        'sharp_turns': sharp_turns,
        'dangerous_intersections': dangerous_intersections
    }

def calculate_turn_angle(prev_point, curr_point, next_point):
    """Calculate the angle of a turn between three points"""
    # Calculate vectors
    vector1 = (
        curr_point['lat'] - prev_point['lat'],
        curr_point['lng'] - prev_point['lng']
    )
    
    vector2 = (
        next_point['lat'] - curr_point['lat'],
        next_point['lng'] - curr_point['lng']
    )
    
    # Calculate dot product
    dot_product = vector1[0] * vector2[0] + vector1[1] * vector2[1]
    
    # Calculate magnitudes
    mag1 = math.sqrt(vector1[0]**2 + vector1[1]**2)
    mag2 = math.sqrt(vector2[0]**2 + vector2[1]**2)
    
    # Calculate angle in degrees
    if mag1 > 0 and mag2 > 0:
        cos_angle = dot_product / (mag1 * mag2)
        # Clamp to valid range for acos
        cos_angle = max(-1, min(1, cos_angle))
        angle_rad = math.acos(cos_angle)
        angle_deg = math.degrees(angle_rad)
    else:
        angle_deg = 0
    
    return {
        'location': {
            'lat': curr_point['lat'],
            'lng': curr_point['lng']
        },
        'angle': angle_deg
    }

def get_road_geometry(points):
    """
    Get road geometry information for route points
    
    In a real implementation, this would call Google Maps Roads API
    or another service. For this demo, we generate synthetic data.
    """
    geometry_data = []
    
    for i, point in enumerate(points):
        # Generate synthetic data
        is_intersection = (i % 10 == 0)  # Roughly every 10th point is an intersection
        
        # Road width varies (narrow roads are higher risk)
        road_width = np.random.normal(8, 2)
        
        # Calculate curvature based on neighboring points
        curvature = 0
        if i > 0 and i < len(points) - 1:
            prev_point = points[i-1]
            next_point = points[i+1]
            
            # Calculate vectors
            vector1 = (
                point['lat'] - prev_point['lat'],
                point['lng'] - prev_point['lng']
            )
            
            vector2 = (
                next_point['lat'] - point['lat'],
                next_point['lng'] - point['lng']
            )
            
            # Calculate angle
            dot_product = vector1[0] * vector2[0] + vector1[1] * vector2[1]
            mag1 = math.sqrt(vector1[0]**2 + vector1[1]**2)
            mag2 = math.sqrt(vector2[0]**2 + vector2[1]**2)
            
            if mag1 > 0 and mag2 > 0:
                cos_angle = dot_product / (mag1 * mag2)
                cos_angle = max(-1, min(1, cos_angle))
                angle_rad = math.acos(cos_angle)
                angle_deg = math.degrees(angle_rad)
                
                # Curvature is inversely related to angle
                # 180 degrees (straight) -> 0 curvature
                # 90 degrees (right angle) -> higher curvature
                curvature = 2 - (angle_deg / 90) if angle_deg <= 180 else 0
        
        # Visibility (in km) - lower visibility is higher risk
        visibility = np.random.normal(10, 3)
        
        # Traffic congestion (0-4) - higher congestion is higher risk
        traffic_congestion = min(4, int(np.random.exponential(1)))
        
        # Road type affects risk
        road_types = ["highway", "primary", "secondary", "residential", "intersection"]
        road_type = np.random.choice(road_types, p=[0.2, 0.3, 0.3, 0.15, 0.05])
        
        # Speed limit (km/h)
        speed_limits = {
            "highway": 100,
            "primary": 80,
            "secondary": 60,
            "residential": 30,
            "intersection": 40
        }
        speed_limit = speed_limits[road_type]
        
        # Road quality (0-10) - lower quality is higher risk
        road_quality = np.random.normal(7, 2).clip(0, 10)
        
        geometry_data.append({
            'location': {
                'lat': point['lat'],
                'lng': point['lng']
            },
            'road_width': road_width,
            'curvature': curvature,
            'visibility': visibility,
            'is_intersection': is_intersection,
            'traffic_congestion': traffic_congestion,
            'road_type': road_type,
            'speed_limit': speed_limit,
            'road_quality': road_quality
        })
    
    return geometry_data

def analyze_historical_accidents(route_points):
    """
    Analyze historical accident data along the route
    
    In a real implementation, this would query accident databases
    or APIs. For this demo, we generate synthetic data.
    """
    # Sample points to reduce computation
    sampled_points = [route_points[i] for i in range(0, len(route_points), max(1, len(route_points) // 20))]
    
    accident_hotspots = []
    
    for point in sampled_points:
        # Synthetic algorithm to determine if a point is an accident hotspot
        # Use lat/lng to seed a pseudo-random generator for consistent results
        seed = int(abs(point['lat'] * 10000) + abs(point['lng'] * 10000))
        np.random.seed(seed)
        
        # 5% chance of being an accident hotspot
        if np.random.random() < 0.05:
            # Generate synthetic accident statistics
            accident_count = np.random.randint(5, 30)
            injury_rate = np.random.random() * 0.5  # 0-50% injury rate
            fatality_rate = np.random.random() * 0.1  # 0-10% fatality rate
            
            # Determine risk level based on statistics
            if accident_count > 20 or fatality_rate > 0.05:
                risk_level = 'High'
            elif accident_count > 10 or injury_rate > 0.25:
                risk_level = 'Medium'
            else:
                risk_level = 'Low'
            
            accident_hotspots.append({
                'location': {
                    'lat': point['lat'],
                    'lng': point['lng']
                },
                'accident_count': accident_count,
                'injury_rate': round(injury_rate * 100, 1),
                'fatality_rate': round(fatality_rate * 100, 1),
                'risk_level': risk_level
            })
    
    return accident_hotspots

def get_speed_limit_recommendation(risk_level):
    """Get recommended speed limit based on risk level"""
    if risk_level == 'High':
        return 30  # km/h
    elif risk_level == 'Medium':
        return 50  # km/h
    else:
        return 80  # km/h

def calculate_route_safety_score(risk_data):
    """Calculate overall safety score for a route (0-10)"""
    if not risk_data:
        return 5, 'Medium'  # Default score
    
    # Count risks by severity
    risk_counts = {
        'high': 0,
        'medium': 0,
        'low': 0
    }
    
    # Count various risk types
    for category in ['accident_risks', 'weather_hazards', 'elevation_risks', 
                    'blind_spots', 'network_coverage']:
        for risk in risk_data.get(category, []):
            level = risk.get('risk_level', '').lower()
            if level in risk_counts:
                risk_counts[level] += 1
    
    # Calculate weighted score
    total_risks = sum(risk_counts.values())
    
    if total_risks == 0:
        return 8, 'Low'  # No risks detected
    
    # Weight: high=5, medium=2, low=1
    weighted_score = (
        5 * risk_counts['high'] + 
        2 * risk_counts['medium'] + 
        1 * risk_counts['low']
    ) / total_risks
    
    # Convert to 0-10 scale (higher is safer)
    # Max possible score is 5, so divide by 5 and multiply by 10, then invert
    safety_score = 10 - min(10, (weighted_score / 5) * 10)
    
    # Determine risk level
    if safety_score < 4:
        risk_level = 'High'
    elif safety_score < 7:
        risk_level = 'Medium'
    else:
        risk_level = 'Low'
    
    return round(safety_score, 1), risk_level

def get_safety_recommendations(risk_data):
    """Generate safety recommendations based on risk data"""
    if not risk_data:
        return []
    
    recommendations = []
    
    # Check for high-risk sharp turns
    elevation_risks = risk_data.get('elevation_risks', [])
    high_elevation_count = sum(1 for risk in elevation_risks if risk.get('risk_level') == 'High')
    
    if high_elevation_count > 0:
        recommendations.append({
            'type': 'Elevation',
            'description': f'Route contains {high_elevation_count} high-risk steep gradients. Use lower gears on descents and maintain safe speeds.',
            'importance': 'High'
        })
    
    # Check for blind spots
    blind_spots = risk_data.get('blind_spots', [])
    high_blind_spots = sum(1 for spot in blind_spots if spot.get('risk_level') == 'High')
    
    if high_blind_spots > 0:
        recommendations.append({
            'type': 'Visibility',
            'description': f'Route contains {high_blind_spots} high-risk blind spots. Reduce speed and use extra caution in these areas.',
            'importance': 'High'
        })
    
    # Check for weather hazards
    weather_hazards = risk_data.get('weather_hazards', [])
    high_weather_count = sum(1 for hazard in weather_hazards if hazard.get('risk_level') == 'High')
    
    if high_weather_count > 0:
        recommendations.append({
            'type': 'Weather',
            'description': f'Route contains {high_weather_count} areas with severe weather conditions. Consider postponing travel or use extreme caution.',
            'importance': 'High'
        })
    
    # Check for network coverage
    network_issues = risk_data.get('network_coverage', [])
    poor_coverage_count = sum(1 for issue in network_issues 
                             if issue.get('risk_level') in ['High', 'Medium'])
    
    if poor_coverage_count > 0:
        recommendations.append({
            'type': 'Communication',
            'description': f'Route has {poor_coverage_count} areas with poor network coverage. Prepare alternate communication methods.',
            'importance': 'Medium'
        })
    
    # Check for accident hotspots
    accident_risks = risk_data.get('accident_risks', [])
    hotspot_count = len(accident_risks)
    
    if hotspot_count > 0:
        recommendations.append({
            'type': 'Accident Hotspots',
            'description': f'Route contains {hotspot_count} accident-prone areas. Exercise heightened awareness in these locations.',
            'importance': 'High'
        })
    
    # Check for eco-sensitive zones
    eco_zones = risk_data.get('eco_sensitive_zones', [])
    
    if eco_zones:
        recommendations.append({
            'type': 'Environmental',
            'description': f'Route passes through {len(eco_zones)} environmentally sensitive areas. Observe speed limits and wildlife warnings.',
            'importance': 'Medium'
        })
    
    # Check for emergency facilities
    nearby_facilities = risk_data.get('nearby_facilities', {})
    hospitals = nearby_facilities.get('hospitals', [])
    
    if not hospitals:
        recommendations.append({
            'type': 'Emergency Services',
            'description': 'Limited access to hospitals along this route. Ensure adequate first aid supplies are available.',
            'importance': 'Medium'
        })
    
    return recommendations

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km using Haversine formula"""
    R = 6371  # Earth radius in km
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return distance