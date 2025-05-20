import requests
import dash_leaflet as dl
from dash import html
from flask import session
import json
import os

# Get backend URL from environment variable
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')

def get_api_data(endpoint, use_session=False, raw_response=False):
    """
    Utility function to get data from API
    
    Args:
        endpoint: API endpoint to call
        use_session: Whether to use session token for authentication
        raw_response: Whether to return raw response object
    
    Returns:
        Response data or None if error
    """
    try:
        # Ensure endpoint starts with / but remove any trailing /
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        
        url = f"{BACKEND_URL}{endpoint}"
        
        headers = {}
        if use_session and 'access_token' in session:
            headers['Authorization'] = f'Bearer {session["access_token"]}'
        
        response = requests.get(url, headers=headers)
        
        if raw_response:
            return response
        
        if response.status_code == 200:
            return response.json()
        
        return None
    except Exception as e:
        print(f"Error getting API data: {str(e)}")
        return None

def make_map(children, center=None, zoom=7):
    """
    Create a Leaflet map component
    
    Args:
        children: Map overlays (markers, polylines, etc.)
        center: Map center coordinates [lat, lng]
        zoom: Initial zoom level
    
    Returns:
        Dash Leaflet map component
    """
    # Default center if not provided
    if center is None:
        center = [20.5937, 78.9629]  # Default to center of India
    
    return dl.Map(
        children=[
            dl.TileLayer(
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            ),
            *children
        ],
        center=center,
        zoom=zoom,
        style={'width': '100%', 'height': '100%'}
    )

def get_risk_color(risk_level):
    """
    Get color based on risk level
    
    Args:
        risk_level: Risk level (high, medium, low, unknown)
    
    Returns:
        Hex color code
    """
    risk_level = risk_level.lower() if risk_level else "unknown"
    
    if risk_level == "high":
        return "#FF5252"
    elif risk_level == "medium":
        return "#FFC107"
    elif risk_level == "low":
        return "#4CAF50"
    else:
        return "#9E9E9E"

def get_risk_badge_color(risk_level):
    """
    Get Bootstrap badge color for risk level
    
    Args:
        risk_level: Risk level (high, medium, low, unknown)
    
    Returns:
        Bootstrap color class
    """
    risk_level = risk_level.lower() if risk_level else "unknown"
    
    if risk_level == "high":
        return "danger"
    elif risk_level == "medium":
        return "warning"
    elif risk_level == "low":
        return "success"
    else:
        return "secondary"

def format_timestamp(timestamp):
    """
    Format timestamp for display
    
    Args:
        timestamp: Timestamp string or datetime
    
    Returns:
        Formatted timestamp string
    """
    from datetime import datetime
    
    if isinstance(timestamp, str):
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return timestamp
    else:
        dt = timestamp
    
    return dt.strftime("%Y-%m-%d %H:%M:%S")