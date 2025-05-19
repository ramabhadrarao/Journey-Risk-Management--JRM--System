# backend/services/eta_optimizer.py
import os
import numpy as np
import pandas as pd
import pickle
import xgboost as xgb
import datetime
from flask import current_app
from config import MODEL_FOLDER

def optimize_eta(route_points, vehicle_type='car', weather_data=None):
    """
    Optimize ETA based on traffic, weather, and vehicle characteristics
    
    Args:
        route_points: List of dictionaries with lat, lng coordinates
        vehicle_type: Type of vehicle (car, truck, bus, etc.)
        weather_data: Weather hazard data if available
        
    Returns:
        Optimized duration in minutes
    """
    # Get original duration from Google Maps data
    from services.google_maps import get_route_details
    
    if not route_points or len(route_points) < 2:
        return None
    
    # Load pre-trained model
    model_path = os.path.join(MODEL_FOLDER, 'eta_optimization', 'model.pkl')
    
    try:
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
    except (FileNotFoundError, EOFError):
        # If model doesn't exist, train a new one
        model = train_eta_model()
    
    # Get traffic data
    from services.google_maps import get_traffic_data
    traffic_data = get_traffic_data(route_points)
    
    # Get or reuse weather data
    if not weather_data:
        from services.weather_service import get_weather_hazards
        weather_data = get_weather_hazards(route_points)
    
    # Calculate route segments
    segments = []
    for i in range(len(route_points) - 1):
        # Calculate segment distance
        from services.weather_service import calculate_distance
        distance = calculate_distance(
            route_points[i]['lat'], route_points[i]['lng'],
            route_points[i+1]['lat'], route_points[i+1]['lng']
        )
        
        # Skip if distance is too small
        if distance < 0.01:  # 10 meters
            continue
        
        # Find closest traffic data
        traffic = None
        min_dist = float('inf')
        
        for t in traffic_data:
            dist1 = calculate_distance(
                route_points[i]['lat'], route_points[i]['lng'],
                t['location']['lat'], t['location']['lng']
            )
            dist2 = calculate_distance(
                route_points[i+1]['lat'], route_points[i+1]['lng'],
                t['location']['lat'], t['location']['lng']
            )
            
            avg_dist = (dist1 + dist2) / 2
            if avg_dist < min_dist:
                min_dist = avg_dist
                traffic = t
        
        # Find closest weather hazard
        weather = None
        min_dist = float('inf')
        
        for w in weather_data:
            dist1 = calculate_distance(
                route_points[i]['lat'], route_points[i]['lng'],
                w['location']['lat'], w['location']['lng']
            )
            dist2 = calculate_distance(
                route_points[i+1]['lat'], route_points[i+1]['lng'],
                w['location']['lat'], w['location']['lng']
            )
            
            avg_dist = (dist1 + dist2) / 2
            if avg_dist < min_dist and avg_dist < 5:  # Within 5 km
                min_dist = avg_dist
                weather = w
        
        # Create segment with features
        segment = {
            'start': {
                'lat': route_points[i]['lat'],
                'lng': route_points[i]['lng']
            },
            'end': {
                'lat': route_points[i+1]['lat'],
                'lng': route_points[i+1]['lng']
            },
            'distance': distance,
            'congestion': traffic['congestion_level'] if traffic else 0,
            'speed_limit': traffic['speed_limit'] if traffic else 50,
            'road_type': traffic['road_type'] if traffic else 'unknown',
            'is_highway': 1 if (traffic and traffic['road_type'] == 'highway') else 0,
            'vehicle_type': encode_vehicle_type(vehicle_type),
            'time_of_day': datetime.datetime.utcnow().hour,
            'is_weekend': 1 if datetime.datetime.utcnow().weekday() >= 5 else 0
        }
        
        # Add weather features if available
        if weather:
            segment.update({
                'temperature': weather['temperature'],
                'visibility': weather['visibility'],
                'precipitation': weather['precipitation'],
                'wind_speed': weather['wind_speed'],
                'weather_risk': encode_risk_level(weather['risk_level'])
            })
        else:
            segment.update({
                'temperature': 20,
                'visibility': 10,
                'precipitation': 0,
                'wind_speed': 0,
                'weather_risk': 0
            })
        
        segments.append(segment)
    
    if not segments:
        return None
    
    # Prepare features for model
    features = pd.DataFrame([
        {
            'distance': segment['distance'],
            'congestion': segment['congestion'],
            'speed_limit': segment['speed_limit'],
            'is_highway': segment['is_highway'],
            'vehicle_type': segment['vehicle_type'],
            'time_of_day': segment['time_of_day'],
            'is_weekend': segment['is_weekend'],
            'temperature': segment['temperature'],
            'visibility': segment['visibility'],
            'precipitation': segment['precipitation'],
            'wind_speed': segment['wind_speed'],
            'weather_risk': segment['weather_risk']
        }
        for segment in segments
    ])
    
    # Predict travel time for each segment
    predictions = model.predict(features)
    
    # Sum up segment times
    total_time = sum(predictions)
    
    # Convert to minutes and format
    minutes = round(total_time)
    
    # Format duration
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours > 0:
        formatted_duration = f"{hours} hours {remaining_minutes} mins"
    else:
        formatted_duration = f"{remaining_minutes} mins"
    
    return formatted_duration

def train_eta_model():
    """Train a new ETA optimization model"""
    current_app.logger.info("Training new ETA optimization model")
    
    # In a real-world scenario, you would load historical route and travel time data,
    # and train a model. For demonstration, create a synthetic model.
    
    # Create synthetic training data
    np.random.seed(42)
    n_samples = 5000
    
    # Base travel times (minutes per km) for different road types
    base_times = {
        'highway': 0.6,      # 100 km/h
        'primary': 1.0,      # 60 km/h
        'secondary': 1.5,    # 40 km/h
        'residential': 2.0,  # 30 km/h
        'unknown': 1.2       # 50 km/h
    }
    
    # Vehicle type multipliers
    vehicle_multipliers = {
        'car': 1.0,
        'truck': 1.3,
        'bus': 1.4,
        'motorcycle': 0.9,
        'bicycle': 3.0
    }
    
    # Generate data
    data = []
    for _ in range(n_samples):
        # Generate random segment
        distance = np.random.uniform(0.1, 5.0)  # km
        road_type = np.random.choice(list(base_times.keys()))
        vehicle_type = np.random.choice(list(vehicle_multipliers.keys()))
        
        congestion = np.random.randint(0, 5)
        time_of_day = np.random.randint(0, 24)
        is_weekend = np.random.randint(0, 2)
        
        # Weather conditions
        temperature = np.random.normal(15, 10)
        visibility = np.random.normal(8, 5).clip(0, 20)
        precipitation = np.random.exponential(1)
        wind_speed = np.random.exponential(5)
        weather_risk = np.random.randint(0, 3)
        
        # Calculate base time
        base_time = distance * base_times[road_type] * vehicle_multipliers[vehicle_type]
        
        # Apply modifiers
        modifiers = 1.0
        
        # Congestion modifier (0-100% increase)
        modifiers += 0.2 * congestion
        
        # Time of day modifier
        if 7 <= time_of_day <= 9 or 16 <= time_of_day <= 18:
            modifiers += 0.3  # Rush hour
        elif 22 <= time_of_day or time_of_day <= 5:
            modifiers -= 0.15  # Night time, less traffic
        
        # Weekend modifier
        modifiers -= 0.1 * is_weekend
        
        # Weather modifiers
        modifiers += 0.05 * (precipitation > 0)  # Light rain
        modifiers += 0.2 * (precipitation > 3)   # Heavy rain
        modifiers += 0.3 * (visibility < 3)      # Low visibility
        modifiers += 0.1 * (weather_risk)        # Weather risk level
        
        # Calculate final time with some random noise
        travel_time = base_time * modifiers * np.random.normal(1, 0.05)
        
        # Add to dataset
        data.append({
            'distance': distance,
            'congestion': congestion,
            'speed_limit': 100 if road_type == 'highway' else 50,
            'is_highway': 1 if road_type == 'highway' else 0,
            'vehicle_type': encode_vehicle_type(vehicle_type),
            'time_of_day': time_of_day,
            'is_weekend': is_weekend,
            'temperature': temperature,
            'visibility': visibility,
            'precipitation': precipitation,
            'wind_speed': wind_speed,
            'weather_risk': weather_risk,
            'travel_time': travel_time
        })
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Train model
    X = df.drop('travel_time', axis=1)
    y = df['travel_time']
    
    model = xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)
    model.fit(X, y)
    
    # Save model
    os.makedirs(os.path.join(MODEL_FOLDER, 'eta_optimization'), exist_ok=True)
    model_path = os.path.join(MODEL_FOLDER, 'eta_optimization', 'model.pkl')
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    return model

def update_eta_model():
    """Update the ETA optimization model with new data"""
    current_app.logger.info("Updating ETA optimization model")
    
    # In a real-world scenario, you would fetch new travel time data
    # and update the model. For demonstration, just train a new model.
    train_eta_model()

def encode_vehicle_type(vehicle_type):
    """Encode vehicle type as integer"""
    vehicle_types = {
        'car': 0,
        'truck': 1,
        'bus': 2,
        'motorcycle': 3,
        'bicycle': 4,
        'unknown': 5
    }
    
    return vehicle_types.get(vehicle_type.lower(), 5)

def encode_risk_level(risk_level):
    """Encode risk level as integer"""
    risk_levels = {
        'low': 0,
        'medium': 1,
        'high': 2,
        'unknown': 0
    }
    
    return risk_levels.get(risk_level.lower(), 0)