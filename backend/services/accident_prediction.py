# backend/services/accident_prediction.py
import os
import numpy as np
import pandas as pd
import pickle
import datetime
from sklearn.ensemble import RandomForestClassifier
from flask import current_app
from config import MODEL_FOLDER

def predict_accident_risks(route_points):
    """
    Predict accident risks for route points
    
    Args:
        route_points: List of dictionaries with lat, lng coordinates
        
    Returns:
        List of accident risk points with risk level and probability
    """
    # Load pre-trained model
    model_path = os.path.join(MODEL_FOLDER, 'accident_risk', 'model.pkl')
    
    try:
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
    except (FileNotFoundError, EOFError):
        # If model doesn't exist, train a new one
        model = train_accident_model()
    
    # Prepare input data
    if not route_points:
        return []
    
    # Get current time
    now = datetime.datetime.utcnow()
    
    # Get weather data for points
    from services.weather_service import get_weather_data
    weather_data = get_weather_data(route_points)
    
    # Get traffic data for points
    from services.google_maps import get_traffic_data
    traffic_data = get_traffic_data(route_points)
    
    # Prepare features for each point
    features = []
    
    for i, point in enumerate(route_points):
        # Only process a sample of points for efficiency (every 10th point)
        if i % 10 != 0:
            continue
        
        # Get weather for this point
        point_weather = next((w for w in weather_data if 
                              w['location']['lat'] == point['lat'] and 
                              w['location']['lng'] == point['lng']), {})
        
        # Get traffic for this point
        point_traffic = next((t for t in traffic_data if 
                             t['location']['lat'] == point['lat'] and 
                             t['location']['lng'] == point['lng']), {})
        
        # Extract features
        feature_dict = {
            'hour_of_day': now.hour,
            'day_of_week': now.weekday(),
            'is_weekend': 1 if now.weekday() >= 5 else 0,
            'is_holiday': 0,  # Would need holiday API
            'latitude': point['lat'],
            'longitude': point['lng'],
            'precipitation': point_weather.get('precipitation', 0),
            'temperature': point_weather.get('temperature', 20),
            'visibility': point_weather.get('visibility', 10),
            'wind_speed': point_weather.get('wind_speed', 0),
            'traffic_congestion': point_traffic.get('congestion_level', 0),
            'speed_limit': point_traffic.get('speed_limit', 50),
            'road_type': encode_road_type(point_traffic.get('road_type', 'unknown'))
        }
        
        features.append((point, feature_dict))
    
    if not features:
        return []
    
    # Convert to DataFrame
    feature_df = pd.DataFrame([f[1] for f in features])
    
    # Make predictions
    probabilities = model.predict_proba(feature_df)
    
    # Process results
    accident_risks = []
    
    for i, (point, _) in enumerate(features):
        probability = float(probabilities[i][1])  # Probability of accident
        
        # Determine risk level
        if probability >= 0.7:
            risk_level = 'High'
        elif probability >= 0.4:
            risk_level = 'Medium'
        else:
            risk_level = 'Low'
        
        accident_risks.append({
            'location': {
                'lat': point['lat'],
                'lng': point['lng']
            },
            'risk_level': risk_level,
            'probability': round(probability, 3),
            'factors': get_risk_factors(features[i][1], probability)
        })
    
    return accident_risks

def train_accident_model():
    """Train a new accident prediction model"""
    current_app.logger.info("Training new accident prediction model")
    
    # In a real-world scenario, you would load historical accident data,
    # feature engineer, and train a model. For demonstration, create a dummy model.
    
    # Create dummy training data
    np.random.seed(42)
    n_samples = 1000
    
    X = pd.DataFrame({
        'hour_of_day': np.random.randint(0, 24, n_samples),
        'day_of_week': np.random.randint(0, 7, n_samples),
        'is_weekend': np.random.randint(0, 2, n_samples),
        'is_holiday': np.random.randint(0, 2, n_samples),
        'latitude': np.random.uniform(25, 45, n_samples),
        'longitude': np.random.uniform(-125, -65, n_samples),
        'precipitation': np.random.exponential(2, n_samples),
        'temperature': np.random.normal(20, 10, n_samples),
        'visibility': np.random.normal(10, 5, n_samples).clip(0, 20),
        'wind_speed': np.random.exponential(10, n_samples),
        'traffic_congestion': np.random.randint(0, 5, n_samples),
        'speed_limit': np.random.choice([30, 50, 70, 90, 110], n_samples),
        'road_type': np.random.randint(0, 6, n_samples)
    })
    
    # Generate target variable (accident occurred)
    # Higher probability for certain conditions
    accident_prob = (
        0.05 +  # base rate
        0.02 * (X['hour_of_day'] >= 22).astype(int) +  # late night
        0.02 * (X['hour_of_day'] <= 6).astype(int) +   # early morning
        0.01 * X['is_weekend'] +                       # weekend
        0.02 * X['is_holiday'] +                       # holiday
        0.03 * (X['precipitation'] > 5).astype(int) +  # heavy rain
        0.03 * (X['visibility'] < 3).astype(int) +     # low visibility
        0.02 * (X['wind_speed'] > 15).astype(int) +    # high wind
        0.04 * (X['traffic_congestion'] > 3).astype(int) +  # high congestion
        0.03 * (X['road_type'] == 3).astype(int)       # intersections
    )
    
    y = np.random.binomial(1, accident_prob)
    
    # Train model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # Save model
    os.makedirs(os.path.join(MODEL_FOLDER, 'accident_risk'), exist_ok=True)
    model_path = os.path.join(MODEL_FOLDER, 'accident_risk', 'model.pkl')
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    return model

def update_accident_model():
    """Update the accident prediction model with new data"""
    current_app.logger.info("Updating accident prediction model")
    
    # In a real-world scenario, you would fetch new accident data
    # and update the model. For demonstration, just train a new model.
    train_accident_model()

def encode_road_type(road_type):
    """Encode road type as integer"""
    road_types = {
        'highway': 0,
        'primary': 1,
        'secondary': 2,
        'intersection': 3,
        'residential': 4,
        'unknown': 5
    }
    
    return road_types.get(road_type.lower(), 5)

def get_risk_factors(features, probability):
    """Determine main risk factors contributing to accident probability"""
    risk_factors = []
    
    # Check various conditions that increase risk
    if features['hour_of_day'] >= 22 or features['hour_of_day'] <= 6:
        risk_factors.append({
            'factor': 'Time of day',
            'description': 'Driving during late night or early morning hours'
        })
    
    if features['is_weekend'] == 1:
        risk_factors.append({
            'factor': 'Weekend',
            'description': 'Weekend driving has higher accident rates'
        })
    
    if features['precipitation'] > 5:
        risk_factors.append({
            'factor': 'Weather',
            'description': 'Heavy precipitation reducing visibility and traction'
        })
    
    if features['visibility'] < 3:
        risk_factors.append({
            'factor': 'Visibility',
            'description': 'Low visibility conditions'
        })
    
    if features['wind_speed'] > 15:
        risk_factors.append({
            'factor': 'Wind',
            'description': 'High wind speeds affecting vehicle stability'
        })
    
    if features['traffic_congestion'] > 3:
        risk_factors.append({
            'factor': 'Traffic',
            'description': 'Heavy traffic congestion'
        })
    
    if features['road_type'] == 3:  # intersection
        risk_factors.append({
            'factor': 'Road type',
            'description': 'Intersection with crossing traffic'
        })
    
    # If no specific factors, add a generic one based on probability
    if not risk_factors:
        if probability >= 0.7:
            risk_factors.append({
                'factor': 'Multiple factors',
                'description': 'Combination of various risk factors'
            })
        elif probability >= 0.4:
            risk_factors.append({
                'factor': 'Moderate risk',
                'description': 'Standard driving conditions with some risk factors'
            })
        else:
            risk_factors.append({
                'factor': 'Low risk',
                'description': 'Generally safe driving conditions'
            })
    
    return risk_factors