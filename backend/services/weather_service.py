# backend/services/weather_service.py
import requests
import os
import pickle
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from flask import current_app
from config import OPENWEATHER_API_KEY, MODEL_FOLDER
import datetime
import time
import math

def get_weather_data(route_points):
    """
    Get weather data for the given route points
    
    Args:
        route_points: List of dictionaries with lat, lng coordinates
        
    Returns:
        List of weather data points
    """
    if not route_points:
        return []
    
    # Sample points to reduce API calls (take every 20th point)
    sampled_points = [point for i, point in enumerate(route_points) if i % 20 == 0]
    
    # Ensure we have at least 3 points (start, middle, end)
    if len(sampled_points) < 3 and len(route_points) >= 3:
        sampled_points = [
            route_points[0],
            route_points[len(route_points) // 2],
            route_points[-1]
        ]
    
    # Get weather for each sampled point
    weather_data = []
    
    for point in sampled_points:
        try:
            # Check if data is in cache
            cache_key = f"weather_{point['lat']}_{point['lng']}"
            cached_data = get_from_cache(cache_key)
            
            if cached_data:
                weather_data.append(cached_data)
                continue
            
            # If not in cache, fetch from API
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                "lat": point['lat'],
                "lon": point['lng'],
                "appid": OPENWEATHER_API_KEY,
                "units": "metric"  # Use metric units
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                weather_point = {
                    'location': {
                        'lat': point['lat'],
                        'lng': point['lng']
                    },
                    'timestamp': datetime.datetime.utcnow(),
                    'temperature': data['main']['temp'],
                    'feels_like': data['main']['feels_like'],
                    'humidity': data['main']['humidity'],
                    'pressure': data['main']['pressure'],
                    'wind_speed': data['wind']['speed'],
                    'wind_direction': data['wind'].get('deg', 0),
                    'cloudiness': data['clouds']['all'],
                    'visibility': data.get('visibility', 10000) / 1000,  # Convert to km
                    'precipitation': 0,
                    'weather_condition': data['weather'][0]['main'],
                    'weather_description': data['weather'][0]['description'],
                    'weather_icon': data['weather'][0]['icon']
                }
                
                # Get precipitation if available
                if 'rain' in data:
                    weather_point['precipitation'] = data['rain'].get('1h', 0)
                elif 'snow' in data:
                    weather_point['precipitation'] = data['snow'].get('1h', 0)
                
                # Cache the data
                save_to_cache(cache_key, weather_point, expiration=1800)  # 30 minutes
                
                weather_data.append(weather_point)
                
                # Rate limit to avoid API throttling
                time.sleep(0.1)
            
        except Exception as e:
            current_app.logger.error(f"Error fetching weather data: {str(e)}")
    
    # Interpolate weather for all points
    if weather_data:
        return interpolate_weather_for_all_points(route_points, weather_data)
    
    return []

def interpolate_weather_for_all_points(route_points, weather_data):
    """
    Interpolate weather data for all route points based on the fetched samples
    
    Args:
        route_points: All route points
        weather_data: Weather data for sampled points
        
    Returns:
        Weather data for all points
    """
    # If we only have weather for one point, use it for all points
    if len(weather_data) == 1:
        return [weather_data[0]] * len(route_points)
    
    # Create dictionary to store interpolated weather
    all_weather = []
    
    # Process each point in the route
    for point in route_points:
        # Find the closest two weather points
        distances = []
        for w_point in weather_data:
            dist = calculate_distance(
                point['lat'], point['lng'],
                w_point['location']['lat'], w_point['location']['lng']
            )
            distances.append((dist, w_point))
        
        # Sort by distance
        distances.sort(key=lambda x: x[0])
        
        # If point is very close to a weather point, use that data
        if distances[0][0] < 5:  # Less than 5 km
            all_weather.append(distances[0][1])
            continue
        
        # Otherwise, interpolate between the two closest points
        w1 = distances[0][1]
        w2 = distances[1][1]
        
        d1 = distances[0][0]
        d2 = distances[1][0]
        
        # Avoid division by zero
        if d1 + d2 == 0:
            all_weather.append(w1)
            continue
        
        # Calculate weights for interpolation
        w1_weight = 1 - (d1 / (d1 + d2))
        w2_weight = 1 - (d2 / (d1 + d2))
        
        # Interpolate numeric values
        numeric_fields = [
            'temperature', 'feels_like', 'humidity', 'pressure',
            'wind_speed', 'cloudiness', 'visibility', 'precipitation'
        ]
        
        interpolated = {
            'location': {
                'lat': point['lat'],
                'lng': point['lng']
            },
            'timestamp': datetime.datetime.utcnow()
        }
        
        for field in numeric_fields:
            interpolated[field] = (
                w1[field] * w1_weight + 
                w2[field] * w2_weight
            )
        
        # Use the condition from the closest point
        interpolated['weather_condition'] = w1['weather_condition']
        interpolated['weather_description'] = w1['weather_description']
        interpolated['weather_icon'] = w1['weather_icon']
        
        all_weather.append(interpolated)
    
    return all_weather

def get_weather_hazards(route_points):
    """
    Analyze weather data to identify hazards
    
    Args:
        route_points: List of dictionaries with lat, lng coordinates
        
    Returns:
        List of weather hazard points with risk level
    """
    # Get weather data
    weather_data = get_weather_data(route_points)
    
    if not weather_data:
        return []
    
    # Load hazard prediction model
    model_path = os.path.join(MODEL_FOLDER, 'weather_hazard', 'model.pkl')
    
    try:
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
    except (FileNotFoundError, EOFError):
        # If model doesn't exist, train a new one
        model = train_weather_hazard_model()
    
    # Prepare input data for model
    features = []
    
    for weather in weather_data:
        feature_dict = {
            'temperature': weather['temperature'],
            'visibility': weather['visibility'],
            'wind_speed': weather['wind_speed'],
            'precipitation': weather['precipitation'],
            'cloudiness': weather['cloudiness'],
            'humidity': weather['humidity']
        }
        
        features.append((weather, feature_dict))
    
    # Convert to DataFrame
    feature_df = pd.DataFrame([f[1] for f in features])
    
    # Make predictions
    probabilities = model.predict_proba(feature_df)
    
    # Process results
    weather_hazards = []
    
    for i, (weather, _) in enumerate(features):
        probability = float(probabilities[i][1])  # Probability of hazard
        
        # Determine risk level
        if probability >= 0.7:
            risk_level = 'High'
        elif probability >= 0.4:
            risk_level = 'Medium'
        else:
            risk_level = 'Low'
        
        # Skip if risk is low
        if probability < 0.3:
            continue
        
        hazard_types = get_weather_hazard_types(weather)
        
        weather_hazards.append({
            'location': weather['location'],
            'risk_level': risk_level,
            'probability': round(probability, 3),
            'weather_condition': weather['weather_condition'],
            'temperature': round(weather['temperature'], 1),
            'visibility': round(weather['visibility'], 1),
            'wind_speed': round(weather['wind_speed'], 1),
            'precipitation': round(weather['precipitation'], 1),
            'hazard_types': hazard_types
        })
    
    return weather_hazards

def get_weather_hazard_types(weather):
    """Determine specific hazard types based on weather conditions"""
    hazard_types = []
    
    # Check for various weather hazards
    if weather['temperature'] < 0:
        hazard_types.append({
            'type': 'Ice risk',
            'description': 'Temperature below freezing, potential for ice on road'
        })
    
    if weather['precipitation'] > 5:
        hazard_types.append({
            'type': 'Heavy precipitation',
            'description': 'Heavy rain or snow reducing visibility and traction'
        })
    elif weather['precipitation'] > 2:
        hazard_types.append({
            'type': 'Moderate precipitation',
            'description': 'Moderate rain or snow may affect road conditions'
        })
    
    if weather['visibility'] < 1:
        hazard_types.append({
            'type': 'Severe visibility reduction',
            'description': 'Visibility less than 1 km, extreme caution required'
        })
    elif weather['visibility'] < 3:
        hazard_types.append({
            'type': 'Poor visibility',
            'description': 'Reduced visibility may affect driving conditions'
        })
    
    if weather['wind_speed'] > 20:
        hazard_types.append({
            'type': 'Strong winds',
            'description': 'High winds may affect vehicle stability'
        })
    
    if 'thunderstorm' in weather['weather_description'].lower():
        hazard_types.append({
            'type': 'Thunderstorm',
            'description': 'Lightning and potentially heavy rain'
        })
    
    if 'fog' in weather['weather_description'].lower():
        hazard_types.append({
            'type': 'Fog',
            'description': 'Reduced visibility due to fog'
        })
    
    # If no specific hazards, add a generic one
    if not hazard_types:
        if weather['weather_condition'].lower() in ['rain', 'snow', 'drizzle', 'sleet']:
            hazard_types.append({
                'type': 'Precipitation',
                'description': f"{weather['weather_condition']} may affect road conditions"
            })
    
    return hazard_types

def train_weather_hazard_model():
    """Train a new weather hazard prediction model"""
    current_app.logger.info("Training new weather hazard prediction model")
    
    # In a real-world scenario, you would load historical weather and hazard data,
    # and train a model. For demonstration, create a dummy model.
    
    # Create dummy training data
    np.random.seed(42)
    n_samples = 1000
    
    X = pd.DataFrame({
        'temperature': np.random.normal(15, 10, n_samples),
        'visibility': np.random.normal(8, 5, n_samples).clip(0, 20),
        'wind_speed': np.random.exponential(5, n_samples),
        'precipitation': np.random.exponential(1, n_samples),
        'cloudiness': np.random.uniform(0, 100, n_samples),
        'humidity': np.random.uniform(30, 100, n_samples)
    })
    
    # Generate target variable (weather hazard)
    # Higher probability for certain conditions
    hazard_prob = (
        0.1 +  # base rate
        0.3 * (X['temperature'] < 0).astype(int) +  # freezing
        0.2 * (X['precipitation'] > 5).astype(int) +  # heavy rain
        0.4 * (X['visibility'] < 1).astype(int) +  # very low visibility
        0.2 * (X['visibility'] < 3).astype(int) +  # low visibility
        0.2 * (X['wind_speed'] > 15).astype(int)   # high wind
    ).clip(0, 1)
    
    y = np.random.binomial(1, hazard_prob)
    
    # Train model
    model = LogisticRegression(random_state=42)
    model.fit(X, y)
    
    # Save model
    os.makedirs(os.path.join(MODEL_FOLDER, 'weather_hazard'), exist_ok=True)
    model_path = os.path.join(MODEL_FOLDER, 'weather_hazard', 'model.pkl')
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    return model

def update_weather_data():
    """Background task to update weather data for active routes"""
    from models.route import Route
    
    try:
        # Get active routes (created in the last 24 hours)
        day_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        routes = list(db.routes.find({
            'created_at': {'$gte': day_ago},
            'status': 'completed'
        }))
        
        for route in routes:
            try:
                # Decode polyline to get route points
                from services.google_maps import decode_polyline
                route_points = decode_polyline(route.get('polyline', ''))
                
                if not route_points:
                    continue
                
                # Get updated weather
                weather_data = get_weather_data(route_points)
                
                # Get updated hazards
                weather_hazards = []
                for weather in weather_data:
                    # Check if hazardous
                    if (weather['visibility'] < 3 or 
                        weather['precipitation'] > 2 or 
                        weather['temperature'] < 0 or 
                        weather['wind_speed'] > 15):
                        
                        # Determine risk level
                        if (weather['visibility'] < 1 or 
                            weather['precipitation'] > 5):
                            risk_level = 'High'
                        elif (weather['visibility'] < 2 or 
                             weather['precipitation'] > 3 or 
                             weather['temperature'] < -5 or 
                             weather['wind_speed'] > 20):
                            risk_level = 'Medium'
                        else:
                            risk_level = 'Low'
                        
                        hazard_types = get_weather_hazard_types(weather)
                        
                        weather_hazards.append({
                            'location': weather['location'],
                            'risk_level': risk_level,
                            'weather_condition': weather['weather_condition'],
                            'temperature': round(weather['temperature'], 1),
                            'visibility': round(weather['visibility'], 1),
                            'wind_speed': round(weather['wind_speed'], 1),
                            'precipitation': round(weather['precipitation'], 1),
                            'hazard_types': hazard_types
                        })
                
                # Update risk data
                if weather_hazards:
                    from models.risk_data import RiskData
                    RiskData.update(route['route_id'], {
                        'weather_hazards': weather_hazards,
                        'last_updated': datetime.datetime.utcnow()
                    })
                    
                    # Emit real-time update via Socket.IO
                    from app import socketio
                    socketio.emit(f'weather_update_{route["route_id"]}', {
                        'hazards': weather_hazards
                    })
            
            except Exception as e:
                current_app.logger.error(f"Error updating weather for route {route['route_id']}: {str(e)}")
    
    except Exception as e:
        current_app.logger.error(f"Error in update_weather_data task: {str(e)}")

def get_current_weather_alerts(user_id):
    """Get current weather alerts for a user's active routes"""
    from models.route import Route
    
    # Get active routes (created in the last 24 hours)
    day_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    routes = list(db.routes.find({
        'user_id': ObjectId(user_id),
        'created_at': {'$gte': day_ago},
        'status': 'completed'
    }))
    
    alerts = []
    
    for route in routes:
        # Get risk data
        risk_data = db.risk_data.find_one({'route_id': route['route_id']})
        
        if not risk_data:
            continue
        
        # Check for high-risk weather hazards
        for hazard in risk_data.get('weather_hazards', []):
            if hazard.get('risk_level') == 'High':
                alerts.append({
                    'route_id': route['route_id'],
                    'route_name': route.get('name', f"Route {route['route_id'][:8]}"),
                    'alert_type': 'weather',
                    'risk_level': 'High',
                    'location': hazard['location'],
                    'description': f"Severe weather: {hazard['weather_condition']}",
                    'details': hazard.get('hazard_types', [])
                })
    
    return alerts

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

def get_from_cache(key):
    """Get data from cache"""
    try:
        from app import redis_client
        
        data = redis_client.get(key)
        if data:
            return pickle.loads(data)
    except:
        pass
    
    return None

def save_to_cache(key, data, expiration=300):
    """Save data to cache"""
    try:
        from app import redis_client
        
        redis_client.setex(
            key,
            expiration,
            pickle.dumps(data)
        )
    except:
        pass