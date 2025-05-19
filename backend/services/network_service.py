# backend/services/network_service.py
import requests
import os
import numpy as np
import datetime
import math
from flask import current_app
from config import OPENCELLID_API_KEY

def get_network_data(points):
    """
    Get network coverage data for route points
    
    Args:
        points: List of dictionaries with lat, lng coordinates
        
    Returns:
        List of dictionaries with network coverage information
    """
    # Sample points to reduce API calls
    sampled_points = [points[i] for i in range(0, len(points), max(1, len(points) // 30))]
    
    coverage_data = []
    
    # In a real application, use OpenCellID API or similar
    # For this demo, generate synthetic network coverage data
    for point in sampled_points:
        # Generate synthetic data
        coverage = generate_synthetic_coverage(point["lat"], point["lng"])
        coverage_data.append(coverage)
    
    return coverage_data

def get_network_coverage_by_provider(points, provider):
    """
    Get network coverage for a specific provider
    
    Args:
        points: List of dictionaries with lat, lng coordinates
        provider: Network provider name
        
    Returns:
        List of dictionaries with network coverage information
    """
    # Sample points to reduce API calls
    sampled_points = [points[i] for i in range(0, len(points), max(1, len(points) // 30))]
    
    coverage_data = []
    
    for point in sampled_points:
        # Generate synthetic data for specific provider
        coverage = generate_synthetic_coverage(point["lat"], point["lng"], provider)
        coverage_data.append(coverage)
    
    return coverage_data

def generate_synthetic_coverage(lat, lng, provider=None):
    """
    Generate synthetic network coverage data
    
    Args:
        lat: Latitude
        lng: Longitude
        provider: Optional provider name
        
    Returns:
        Dictionary with coverage information
    """
    # Use lat/lng to seed a pseudo-random generator for consistent results
    seed = int(abs(lat * 10000) + abs(lng * 10000))
    np.random.seed(seed)
    
    # Generate random provider if not specified
    if not provider:
        providers = ["Verizon", "AT&T", "T-Mobile", "Sprint"]
        provider = np.random.choice(providers)
    
    # Generate signal strength (0-100)
    # Lower in remote areas (approximated by latitude)
    base_signal = np.random.normal(70, 20)
    
    # Adjust signal based on location (simplified model)
    # More remote areas tend to have worse coverage
    remoteness_factor = min(1, max(0, 1 - (abs(lat) % 1) * 2))
    
    signal_strength = max(0, min(100, base_signal * (0.5 + 0.5 * remoteness_factor)))
    
    # Generate network type
    network_types = ["5G", "4G", "3G", "2G"]
    network_weights = [0.3, 0.5, 0.15, 0.05]
    
    # Adjust weights based on signal strength
    if signal_strength < 30:
        network_weights = [0.0, 0.2, 0.5, 0.3]  # Worse signal, more likely to have older network
    elif signal_strength < 60:
        network_weights = [0.1, 0.4, 0.4, 0.1]
    
    network_type = np.random.choice(network_types, p=network_weights)
    
    return {
        "location": {
            "lat": lat,
            "lng": lng
        },
        "provider": provider,
        "network_type": network_type,
        "signal_strength": round(signal_strength, 1),
        "data_speed": calculate_data_speed(network_type, signal_strength),
        "timestamp": datetime.datetime.utcnow()
    }

def calculate_data_speed(network_type, signal_strength):
    """Calculate synthetic data speed based on network type and signal strength"""
    # Base speeds in Mbps
    base_speeds = {
        "5G": 100,
        "4G": 20,
        "3G": 3,
        "2G": 0.1
    }
    
    # Adjust based on signal strength (50% at min signal, 100% at max signal)
    signal_factor = 0.5 + (signal_strength / 100) * 0.5
    
    # Add some random variation
    random_factor = np.random.normal(1, 0.2)
    
    speed = base_speeds[network_type] * signal_factor * random_factor
    
    return round(max(0.1, speed), 1)  # Mbps