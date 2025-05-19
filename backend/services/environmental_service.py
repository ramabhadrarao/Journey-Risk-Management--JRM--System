# backend/services/environmental_service.py
import requests
import os
import numpy as np
import datetime
import math
from flask import current_app

def get_eco_zones(points):
    """
    Get eco-sensitive zones for the given route points
    
    Args:
        points: List of dictionaries with lat, lng coordinates
        
    Returns:
        List of dictionaries with eco-sensitive zone information
    """
    # Sample points to reduce API calls
    sampled_points = [points[i] for i in range(0, len(points), max(1, len(points) // 50))]
    
    # In a real application, would use an environmental API
    # For this demo, generate synthetic eco-sensitive zone data
    eco_zones = []
    
    for point in sampled_points:
        # Generate synthetic data
        if is_in_eco_zone(point["lat"], point["lng"]):
            zone = generate_eco_zone(point["lat"], point["lng"])
            eco_zones.append(zone)
    
    return eco_zones

def is_in_eco_zone(lat, lng):
    """
    Check if a point is in an eco-sensitive zone
    
    Args:
        lat: Latitude
        lng: Longitude
        
    Returns:
        Boolean indicating if the point is in an eco-sensitive zone
    """
    # Use lat/lng to seed a pseudo-random generator for consistent results
    seed = int(abs(lat * 10000) + abs(lng * 10000))
    np.random.seed(seed)
    
    # 10% chance of being in an eco-sensitive zone
    return np.random.random() < 0.1

def generate_eco_zone(lat, lng):
    """
    Generate synthetic eco-sensitive zone data
    
    Args:
        lat: Latitude
        lng: Longitude
        
    Returns:
        Dictionary with eco-sensitive zone information
    """
    # Use lat/lng to seed a pseudo-random generator for consistent results
    seed = int(abs(lat * 10000) + abs(lng * 10000))
    np.random.seed(seed)
    
    # Zone types
    zone_types = [
        "Wildlife Reserve",
        "National Park",
        "Forest Reserve",
        "Protected Watershed",
        "Wetland Reserve",
        "Biodiversity Hotspot"
    ]
    
    # Restriction types
    restriction_types = [
        "Speed Limit Reduction",
        "No Honking",
        "Wildlife Crossing Area",
        "No Stopping",
        "Restricted Hours",
        "Hazardous Materials Prohibition"
    ]
    
    # Generate random zone name
    zone_type = np.random.choice(zone_types)
    
    # Common naming patterns for ecological zones
    location_prefixes = ["Northern", "Eastern", "Western", "Southern", "Central", "Upper", "Lower"]
    location_features = ["Valley", "Ridge", "Hills", "Plains", "Basin", "Mountains", "Forest"]
    
    prefix = np.random.choice(location_prefixes)
    feature = np.random.choice(location_features)
    
    zone_name = f"{prefix} {feature} {zone_type}"
    
    # Generate random restrictions
    num_restrictions = np.random.randint(1, 4)
    restrictions = []
    
    for _ in range(num_restrictions):
        restriction = np.random.choice(restriction_types)
        if restriction not in restrictions:
            restrictions.append(restriction)
    
    return {
        "location": {
            "lat": lat,
            "lng": lng
        },
        "name": zone_name,
        "type": zone_type,
        "restrictions": restrictions
    }

def get_environmental_hazards(points):
    """
    Get environmental hazards for the given route points
    
    Args:
        points: List of dictionaries with lat, lng coordinates
        
    Returns:
        List of dictionaries with environmental hazard information
    """
    # Sample points to reduce API calls
    sampled_points = [points[i] for i in range(0, len(points), max(1, len(points) // 50))]
    
    # In a real application, would use an environmental API
    # For this demo, generate synthetic environmental hazard data
    hazards = []
    
    for point in sampled_points:
        # Generate synthetic data
        if has_environmental_hazard(point["lat"], point["lng"]):
            hazard = generate_environmental_hazard(point["lat"], point["lng"])
            hazards.append(hazard)
    
    return hazards

def has_environmental_hazard(lat, lng):
    """
    Check if a point has an environmental hazard
    
    Args:
        lat: Latitude
        lng: Longitude
        
    Returns:
        Boolean indicating if the point has an environmental hazard
    """
    # Use lat/lng to seed a pseudo-random generator for consistent results
    seed = int(abs(lat * 10000) + abs(lng * 10000))
    np.random.seed(seed)
    
    # 5% chance of having an environmental hazard
    return np.random.random() < 0.05

def generate_environmental_hazard(lat, lng):
    """
    Generate synthetic environmental hazard data
    
    Args:
        lat: Latitude
        lng: Longitude
        
    Returns:
        Dictionary with environmental hazard information
    """
    # Use lat/lng to seed a pseudo-random generator for consistent results
    seed = int(abs(lat * 10000) + abs(lng * 10000))
    np.random.seed(seed)
    
    # Hazard types
    hazard_types = [
        "Flood Prone Area",
        "Landslide Risk",
        "Wildfire Hazard",
        "Avalanche Zone",
        "Earthquake Risk Area",
        "Air Quality Concern"
    ]
    
    # Generate random hazard type
    hazard_type = np.random.choice(hazard_types)
    
    # Generate risk level
    risk_levels = ["Low", "Medium", "High"]
    risk_level = np.random.choice(risk_levels, p=[0.5, 0.3, 0.2])
    
    # Generate seasonal flag
    is_seasonal = np.random.random() < 0.7
    
    # Generate seasons if seasonal
    seasons = []
    if is_seasonal:
        all_seasons = ["Spring", "Summer", "Autumn", "Winter"]
        num_seasons = np.random.randint(1, 4)
        seasons = list(np.random.choice(all_seasons, size=num_seasons, replace=False))
    
    return {
        "location": {
            "lat": lat,
            "lng": lng
        },
        "hazard_type": hazard_type,
        "risk_level": risk_level,
        "is_seasonal": is_seasonal,
        "seasons": seasons,
        "data_source": "Environmental Risk Model"
    }

def get_pollutant_levels(lat, lng):
    """
    Get air pollutant levels for a specific location
    
    Args:
        lat: Latitude
        lng: Longitude
        
    Returns:
        Dictionary with pollutant levels
    """
    # Use lat/lng to seed a pseudo-random generator for consistent results
    seed = int(abs(lat * 10000) + abs(lng * 10000))
    np.random.seed(seed)
    
    # Current date and time
    now = datetime.datetime.utcnow()
    
    # Base pollutant levels
    base_levels = {
        "PM2.5": 12,    # μg/m³
        "PM10": 25,     # μg/m³
        "O3": 30,       # ppb
        "NO2": 15,      # ppb
        "SO2": 5,       # ppb
        "CO": 0.5       # ppm
    }
    
    # Adjust based on time of day (worse in rush hours)
    hour = now.hour
    if 7 <= hour <= 9 or 16 <= hour <= 18:
        time_factor = 1.3
    elif 22 <= hour or hour <= 5:
        time_factor = 0.7
    else:
        time_factor = 1.0
    
    # Adjust based on day of week (better on weekends)
    weekday = now.weekday()
    day_factor = 0.8 if weekday >= 5 else 1.0
    
    # Adjust based on location (simplified model)
    # Urban areas tend to have worse air quality
    urban_factor = 1.0 + np.random.random() * 0.5
    
    # Random variation
    random_factor = np.random.normal(1.0, 0.2)
    
    # Calculate final levels
    pollutant_levels = {}
    for pollutant, base_level in base_levels.items():
        level = base_level * time_factor * day_factor * urban_factor * random_factor
        pollutant_levels[pollutant] = round(level, 1)
    
    # Calculate air quality index
    aqi = calculate_aqi(pollutant_levels)
    
    return {
        "location": {
            "lat": lat,
            "lng": lng
        },
        "timestamp": now,
        "pollutant_levels": pollutant_levels,
        "aqi": aqi,
        "aqi_category": get_aqi_category(aqi),
        "data_source": "Environmental Model"
    }

def calculate_aqi(pollutant_levels):
    """
    Calculate Air Quality Index from pollutant levels
    
    Args:
        pollutant_levels: Dictionary with pollutant levels
        
    Returns:
        AQI value
    """
    # Simplified AQI calculation
    # In reality, this is more complex and depends on local standards
    
    # Convert levels to AQI
    aqi_values = []
    
    # PM2.5 AQI
    pm25 = pollutant_levels.get("PM2.5", 0)
    if pm25 > 0:
        if pm25 <= 12:
            aqi_values.append(50 * (pm25 / 12))
        elif pm25 <= 35.4:
            aqi_values.append(50 + (50 * (pm25 - 12) / (35.4 - 12)))
        elif pm25 <= 55.4:
            aqi_values.append(100 + (50 * (pm25 - 35.4) / (55.4 - 35.4)))
        else:
            aqi_values.append(150 + (50 * (pm25 - 55.4) / (150.4 - 55.4)))
    
    # O3 AQI
    o3 = pollutant_levels.get("O3", 0)
    if o3 > 0:
        if o3 <= 54:
            aqi_values.append(50 * (o3 / 54))
        elif o3 <= 70:
            aqi_values.append(50 + (50 * (o3 - 54) / (70 - 54)))
        else:
            aqi_values.append(100 + (50 * (o3 - 70) / (85 - 70)))
    
    # Return max AQI
    return int(max(aqi_values)) if aqi_values else 0

def get_aqi_category(aqi):
    """
    Get AQI category from AQI value
    
    Args:
        aqi: AQI value
        
    Returns:
        AQI category
    """
    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Moderate"
    elif aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    elif aqi <= 200:
        return "Unhealthy"
    elif aqi <= 300:
        return "Very Unhealthy"
    else:
        return "Hazardous"