from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from dash.dependencies import Input, Output, State
import os
import json
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Create the Flask app for frontend
app = Flask(__name__, 
           static_folder='static',
           template_folder='templates')
app.secret_key = SECRET_KEY

# Create Dash app instances for different dashboards
dash_app = dash.Dash(
    __name__,
    server=app,
    url_base_pathname='/dash/',
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1'}]
)

dash_risk_analysis = dash.Dash(
    __name__,
    server=app,
    url_base_pathname='/dash/risk-analysis/',
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1'}]
)

dash_vehicle_analysis = dash.Dash(
    __name__,
    server=app,
    url_base_pathname='/dash/vehicle-analysis/',
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1'}]
)

# Configure Dash layouts
from dashboards import (
    main_dashboard_layout,
    risk_analysis_layout,
    vehicle_analysis_layout,
    setup_main_dashboard_callbacks,
    setup_risk_analysis_callbacks,
    setup_vehicle_analysis_callbacks
)

dash_app.layout = main_dashboard_layout
dash_risk_analysis.layout = risk_analysis_layout
dash_vehicle_analysis.layout = vehicle_analysis_layout

# Setup Dash callbacks
setup_main_dashboard_callbacks(dash_app)
setup_risk_analysis_callbacks(dash_risk_analysis)
setup_vehicle_analysis_callbacks(dash_vehicle_analysis)

# Template context processor
@app.context_processor
def inject_user_data():
    """Inject user data into all templates"""
    user_data = None
    if 'access_token' in session:
        try:
            headers = {'Authorization': f'Bearer {session["access_token"]}'}
            response = requests.get(
                f'{BACKEND_URL}/api/auth/profile',
                headers=headers
            )
            if response.status_code == 200:
                user_data = response.json()
        except Exception as e:
            print(f"Error fetching user data: {e}")
    
    return {
        'user': user_data,
        'current_year': datetime.now().year,
        'app_name': 'Journey Risk Management System',
        'backend_url': BACKEND_URL
    }

# Import and register frontend routes
from routes import auth_routes, dashboard_routes, routes_routes, vehicle_routes

app.register_blueprint(auth_routes.bp)
app.register_blueprint(dashboard_routes.bp)
app.register_blueprint(routes_routes.bp)
app.register_blueprint(vehicle_routes.bp)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    # Run the frontend application
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)
