# backend/services/breakdown_predictor.py
import os
import numpy as np
import pandas as pd
import pickle
import datetime
from sklearn.ensemble import RandomForestClassifier
from lifelines import CoxPHFitter
from flask import current_app
from config import MODEL_FOLDER

def predict_breakdown_probability(vehicle, telemetry, maintenance_history):
    """
    Predict the probability of vehicle breakdown
    
    Args:
        vehicle: Vehicle document
        telemetry: Latest telemetry data
        maintenance_history: Maintenance history records
        
    Returns:
        Probability of breakdown in the next 100 km
    """
    # Load model
    model_path = os.path.join(MODEL_FOLDER, 'breakdown_prediction', 'model.pkl')
    
    try:
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
    except (FileNotFoundError, EOFError):
        # If model doesn't exist, train a new one
        model = train_breakdown_model()
    
    # Prepare features
    features = prepare_breakdown_features(vehicle, telemetry, maintenance_history)
    
    # Make prediction
    probability = model.predict_proba(pd.DataFrame([features]))[0][1]
    
    return probability

def prepare_breakdown_features(vehicle, telemetry, maintenance_history):
    """Prepare features for breakdown prediction"""
    # Get current date
    now = datetime.datetime.utcnow()
    
    # Calculate time since last maintenance
    last_service_date = vehicle.get('maintenance', {}).get('last_service_date')
    if last_service_date:
        days_since_service = (now - last_service_date).days
    else:
        days_since_service = 365  # Assume one year if no data
    
    # Calculate vehicle age
    vehicle_year = vehicle.get('year')
    if vehicle_year:
        vehicle_age = now.year - int(vehicle_year)
    else:
        vehicle_age = 5  # Assume 5 years if no data
    
    # Extract telemetry features
    if telemetry:
        engine_temp = telemetry.get('engine_temp', 90)
        oil_pressure = telemetry.get('oil_pressure', 30)
        battery_voltage = telemetry.get('battery_voltage', 12)
        rpm = telemetry.get('rpm', 1500)
        fuel_level = telemetry.get('fuel_level', 50)
    else:
        # Default values if no telemetry
        engine_temp = 90
        oil_pressure = 30
        battery_voltage = 12
        rpm = 1500
        fuel_level = 50
    
    # Count number of maintenance issues in last year
    recent_maintenance = [m for m in maintenance_history 
                         if m.get('date') and (now - m['date']).days <= 365]
    maintenance_issues = len(recent_maintenance)
    
    # Calculate average maintenance interval
    if len(maintenance_history) >= 2:
        maintenance_dates = sorted([m['date'] for m in maintenance_history if m.get('date')])
        intervals = [(maintenance_dates[i] - maintenance_dates[i-1]).days 
                     for i in range(1, len(maintenance_dates))]
        avg_maintenance_interval = sum(intervals) / len(intervals) if intervals else 180
    else:
        avg_maintenance_interval = 180  # Assume 6 months if not enough data
    
    # Return features
    return {
        'vehicle_age': vehicle_age,
        'days_since_service': days_since_service,
        'engine_temp': engine_temp,
        'oil_pressure': oil_pressure,
        'battery_voltage': battery_voltage,
        'rpm': rpm,
        'fuel_level': fuel_level,
        'maintenance_issues': maintenance_issues,
        'avg_maintenance_interval': avg_maintenance_interval,
        'vehicle_type': encode_vehicle_type(vehicle.get('type', 'car'))
    }

def train_breakdown_model():
    """Train a new breakdown prediction model"""
    current_app.logger.info("Training new breakdown prediction model")
    
    # In a real-world scenario, you would load historical vehicle data,
    # and train a model. For demonstration, create a synthetic model.
    
    # Create synthetic training data
    np.random.seed(42)
    n_samples = 3000
    
    # Generate features
    X = pd.DataFrame({
        'vehicle_age': np.random.randint(0, 20, n_samples),
        'days_since_service': np.random.randint(0, 500, n_samples),
        'engine_temp': np.random.normal(90, 15, n_samples),
        'oil_pressure': np.random.normal(30, 10, n_samples),
        'battery_voltage': np.random.normal(12, 1, n_samples),
        'rpm': np.random.normal(1500, 500, n_samples),
        'fuel_level': np.random.uniform(0, 100, n_samples),
        'maintenance_issues': np.random.randint(0, 5, n_samples),
        'avg_maintenance_interval': np.random.normal(180, 60, n_samples),
        'vehicle_type': np.random.randint(0, 6, n_samples)
    })
    
    # Generate breakdown probability
    breakdown_prob = (
        0.05 +  # base rate
        0.02 * (X['vehicle_age'] / 10) +                       # older vehicles
        0.02 * (X['days_since_service'] / 100) +               # time since service
        0.03 * ((X['engine_temp'] > 110) | 
                (X['engine_temp'] < 70)).astype(int) +         # abnormal temp
        0.05 * ((X['oil_pressure'] < 15) | 
                (X['oil_pressure'] > 50)).astype(int) +        # abnormal oil pressure
        0.03 * ((X['battery_voltage'] < 11) | 
                (X['battery_voltage'] > 14)).astype(int) +     # abnormal voltage
        0.02 * (X['maintenance_issues'] > 2).astype(int) +     # many maintenance issues
        0.02 * ((X['avg_maintenance_interval'] > 270) & 
                (X['days_since_service'] > 180)).astype(int) + # irregular maintenance
        0.01 * (X['vehicle_type'] == 1).astype(int)            # truck (higher risk)
    ).clip(0, 1)
    
    y = np.random.binomial(1, breakdown_prob)
    
    # Train model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # Save model
    os.makedirs(os.path.join(MODEL_FOLDER, 'breakdown_prediction'), exist_ok=True)
    model_path = os.path.join(MODEL_FOLDER, 'breakdown_prediction', 'model.pkl')
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    return model

def train_survival_model():
    """Train a survival analysis model for breakdown prediction"""
    # Create synthetic survival data
    np.random.seed(42)
    n_samples = 5000
    
    # Generate features
    data = {
        'vehicle_age': np.random.randint(0, 20, n_samples),
        'days_since_service': np.random.randint(0, 500, n_samples),
        'engine_temp': np.random.normal(90, 15, n_samples),
        'oil_pressure': np.random.normal(30, 10, n_samples),
        'battery_voltage': np.random.normal(12, 1, n_samples),
        'maintenance_issues': np.random.randint(0, 5, n_samples),
        'vehicle_type': np.random.randint(0, 6, n_samples)
    }
    
    # Generate time to breakdown
    baseline_time = np.random.exponential(1000, n_samples)
    
    # Modify time based on features
    for i in range(n_samples):
        vehicle_age_factor = 0.9 ** data['vehicle_age'][i]
        service_factor = 0.95 ** (data['days_since_service'][i] / 30)
        temp_factor = 0.8 if data['engine_temp'][i] > 110 else 1.0
        oil_factor = 0.7 if data['oil_pressure'][i] < 15 else 1.0
        
        baseline_time[i] *= vehicle_age_factor * service_factor * temp_factor * oil_factor
    
    # Generate censored indicator (0=censored, 1=observed breakdown)
    censored = np.random.binomial(1, 0.6, n_samples)
    
    # Create dataframe
    df = pd.DataFrame(data)
    df['duration'] = baseline_time
    df['observed'] = censored
    
    # Train Cox model
    cph = CoxPHFitter()
    cph.fit(df, duration_col='duration', event_col='observed')
    
    # Save model
    os.makedirs(os.path.join(MODEL_FOLDER, 'breakdown_prediction'), exist_ok=True)
    model_path = os.path.join(MODEL_FOLDER, 'breakdown_prediction', 'survival_model.pkl')
    
    with open(model_path, 'wb') as f:
        pickle.dump(cph, f)
    
    return cph

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