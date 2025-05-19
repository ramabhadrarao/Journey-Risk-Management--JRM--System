# backend/services/google_maps.py
import requests
import os
import polyline
import json
import time
import math
from flask import current_app
from config import GOOGLE_MAPS_API_KEY

def get_route_details(origin, destination, waypoints=None):
    """
    Get route details from Google Maps Directions API
    
    Args:
        origin: Origin address or coordinates
        destination: Destination address or coordinates
        waypoints: Optional list of waypoints
        
    Returns:
        Dictionary with route details
    """
    url = "https://maps.googleapis.com/maps/api/directions/json"
    
    # Prepare params
    params = {
        "origin": origin,
        "destination": destination,
        "key": GOOGLE_MAPS_API_KEY,
        "alternatives": "true"  # Get multiple route options
    }
    
    # Add waypoints if provided
    if waypoints:
        params["waypoints"] = "|".join(waypoints)
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data["status"] != "OK":
            current_app.logger.error(f"Error getting directions: {data['status']}")
            return None
        
        # Get the first (recommended) route
        route = data["routes"][0]
        leg = route["legs"][0]  # First leg if no waypoints
        
        # Extract details
        distance = leg["distance"]["text"]
        duration = leg["duration"]["text"]
        polyline_str = route["overview_polyline"]["points"]
        
        # Decode polyline to get route points
        points = decode_polyline(polyline_str)
        
        # Get formatted waypoints
        waypoints = []
        for i, point in enumerate(points):
            # Include start and end points and sample the rest
            if i == 0 or i == len(points) - 1 or i % 10 == 0:
                waypoints.append({
                    "lat": point[0],
                    "lng": point[1]
                })
        
        # Return route details
        return {
            "distance": distance,
            "duration": duration,
            "polyline": polyline_str,
            "waypoints": waypoints,
            "start_location": {
                "lat": leg["start_location"]["lat"],
                "lng": leg["start_location"]["lng"]
            },
            "end_location": {
                "lat": leg["end_location"]["lat"],
                "lng": leg["end_location"]["lng"]
            },
            "steps": [
                {
                    "distance": step["distance"]["text"],
                    "duration": step["duration"]["text"],
                    "instructions": step["html_instructions"],
                    "start_location": {
                        "lat": step["start_location"]["lat"],
                        "lng": step["start_location"]["lng"]
                    },
                    "end_location": {
                        "lat": step["end_location"]["lat"],
                        "lng": step["end_location"]["lng"]
                    }
                }
                for step in leg["steps"]
            ]
        }
    
    except Exception as e:
        current_app.logger.error(f"Error getting route details: {str(e)}")
        return None

def decode_polyline(polyline_str):
    """
    Decode Google Maps polyline string to list of coordinates
    
    Args:
        polyline_str: Encoded polyline string
        
    Returns:
        List of (lat, lng) tuples
    """
    return polyline.decode(polyline_str)

def get_elevation_data(points):
    """
    Get elevation data from Google Maps Elevation API
    
    Args:
        points: List of dictionaries with lat, lng coordinates
        
    Returns:
        List of dictionaries with lat, lng, elevation
    """
    url = "https://maps.googleapis.com/maps/api/elevation/json"
    
    # Process in batches due to URL length limits
    max_points_per_request = 100
    all_results = []
    
    for i in range(0, len(points), max_points_per_request):
        batch = points[i:i + max_points_per_request]
        
        # Convert points to required format
        locations = "|".join([f"{point['lat']},{point['lng']}" for point in batch])
        
        params = {
            "locations": locations,
            "key": GOOGLE_MAPS_API_KEY
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if data["status"] != "OK":
                current_app.logger.error(f"Error getting elevation data: {data['status']}")
                continue
            
            # Extract elevation data
            for j, result in enumerate(data["results"]):
                if i + j < len(points):
                    all_results.append({
                        "lat": points[i + j]["lat"],
                        "lng": points[i + j]["lng"],
                        "elevation": result["elevation"]
                    })
            
            # Avoid rate limits
            time.sleep(0.1)
        
        except Exception as e:
            current_app.logger.error(f"Error getting elevation data: {str(e)}")
    
    return all_results

def get_traffic_data(points):
    """
    Get traffic data from Google Maps Roads API
    
    Args:
        points: List of dictionaries with lat, lng coordinates
        
    Returns:
        List of dictionaries with traffic information
    """
    # Sample points to reduce API calls
    sampled_points = [points[i] for i in range(0, len(points), max(1, len(points) // 50))]
    
    # Get traffic data
    traffic_data = []
    
    for point in sampled_points:
        # In a real application, we would use the Google Maps Roads API
        # For this demo, generate synthetic traffic data
        congestion_level = generate_synthetic_congestion(point["lat"], point["lng"])
        
        traffic_data.append({
            "location": {
                "lat": point["lat"],
                "lng": point["lng"]
            },
            "congestion_level": congestion_level,
            "speed_limit": get_synthetic_speed_limit(congestion_level),
            "road_type": get_synthetic_road_type(point["lat"], point["lng"])
        })
    
    return traffic_data

def get_nearby_places(lat, lng, place_type, radius=1000):
    """
    Get nearby places from Google Maps Places API
    
    Args:
        lat: Latitude
        lng: Longitude
        place_type: Type of place (hospital, police, gas_station, etc.)
        radius: Search radius in meters
        
    Returns:
        List of dictionaries with place information
    """
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    
    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "type": place_type,
        "key": GOOGLE_MAPS_API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data["status"] not in ["OK", "ZERO_RESULTS"]:
            current_app.logger.error(f"Error getting nearby places: {data['status']}")
            return []
        
        places = []
        
        for place in data.get("results", []):
            # Calculate distance
            place_lat = place["geometry"]["location"]["lat"]
            place_lng = place["geometry"]["location"]["lng"]
            
            distance = calculate_distance(lat, lng, place_lat, place_lng) * 1000  # to meters
            
            places.append({
                "place_id": place["place_id"],
                "name": place["name"],
                "vicinity": place.get("vicinity", ""),
                "geometry": place["geometry"],
                "distance": distance
            })
        
        return places
    
    except Exception as e:
        current_app.logger.error(f"Error getting nearby places: {str(e)}")
        return []

def get_road_geometry(points):
    """
    Get road geometry from Google Maps Roads API
    
    Args:
        points: List of dictionaries with lat, lng coordinates
        
    Returns:
        List of dictionaries with road geometry information
    """
    # In a real application, we would use the Google Maps Roads API
    # For this demo, generate synthetic road geometry data
    
    geometry_data = []
    
    for i, point in enumerate(points):
        # Generate synthetic data
        is_intersection = (i % 10 == 0)  # Roughly every 10th point
        road_width = np.random.normal(8, 2)  # meters
        
        # Calculate curvature based on neighboring points
        curvature = 0
        if i > 0 and i < len(points) - 1:
            prev_point = points[i-1]
            next_point = points[i+1]
            
            # Calculate vectors
            vector1 = (
                point["lat"] - prev_point["lat"],
                point["lng"] - prev_point["lng"]
            )
            
            vector2 = (
                next_point["lat"] - point["lat"],
                next_point["lng"] - point["lng"]
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
        
        # Calculate visibility
        visibility = np.random.normal(10, 3)  # km
        
        # Calculate gradient
        gradient = np.random.normal(0, 3)  # percent
        
        geometry_data.append({
            "location": {
                "lat": point["lat"],
                "lng": point["lng"]
            },
            "road_width": road_width,
            "curvature": curvature,
            "gradient": gradient,
            "visibility": visibility,
            "is_intersection": is_intersection
        })
    
    return geometry_data

def generate_synthetic_congestion(lat, lng):
    """Generate synthetic traffic congestion level (0-4)"""
    # Use lat/lng to seed a pseudo-random generator for consistent results
    seed = int(abs(lat * 1000) + abs(lng * 1000))
    np.random.seed(seed)
    
    # Higher chance of congestion in certain patterns
    hour = datetime.datetime.now().hour
    
    # Rush hour congestion
    if 7 <= hour <= 9 or 16 <= hour <= 18:
        return min(4, int(np.random.exponential(2)))
    else:
        return min(4, int(np.random.exponential(1)))

def get_synthetic_speed_limit(congestion_level):
    """Get synthetic speed limit based on congestion"""
    # Base speed limits for different road types
    base_limits = [100, 80, 60, 50, 30]
    
    # Choose a base limit
    base_limit = np.random.choice(base_limits)
    
    # Adjust based on congestion
    if congestion_level >= 3:
        return max(30, base_limit - 30)
    elif congestion_level >= 1:
        return max(30, base_limit - 10)
    else:
        return base_limit

def get_synthetic_road_type(lat, lng):
    """Get synthetic road type"""
    # Use lat/lng to seed a pseudo-random generator for consistent results
    seed = int(abs(lat * 10000) + abs(lng * 10000))
    np.random.seed(seed)
    
    road_types = ["highway", "primary", "secondary", "residential", "intersection"]
    weights = [0.2, 0.3, 0.3, 0.15, 0.05]
    
    return np.random.choice(road_types, p=weights)

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