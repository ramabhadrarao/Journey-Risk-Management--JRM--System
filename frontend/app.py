from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_assets import Environment, Bundle
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import os
import json
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the backend app
from backend.app import app as backend_app

# Create the Flask app for frontend
frontend_app = Flask(__name__, 
                    static_folder='static',
                    template_folder='templates')
frontend_app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Configure Flask-Assets
assets = Environment(frontend_app)
assets.debug = frontend_app.debug

# Define asset bundles
scss = Bundle('scss/tabler.scss', filters='libsass', output='css/tabler.css')
css = Bundle('css/custom.css', 'css/tabler.css', filters='cssmin', output='css/packed.css')
js = Bundle('js/tabler.js', 'js/custom.js', filters='jsmin', output='js/packed.js')

assets.register('scss_all', scss)
assets.register('css_all', css)
assets.register('js_all', js)

# Create Dash app instances for different dashboards
dash_app = dash.Dash(
    __name__,
    server=frontend_app,
    url_base_pathname='/dash/',
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1'}]
)

dash_risk_analysis = dash.Dash(
    __name__,
    server=frontend_app,
    url_base_pathname='/dash/risk-analysis/',
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1'}]
)

dash_vehicle_analysis = dash.Dash(
    __name__,
    server=frontend_app,
    url_base_pathname='/dash/vehicle-analysis/',
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1'}]
)

# Configure Dash layouts
from frontend.dashboards import (
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
@frontend_app.context_processor
def inject_user_data():
    """Inject user data into all templates"""
    user_data = None
    if 'access_token' in session:
        try:
            headers = {'Authorization': f'Bearer {session["access_token"]}'}
            response = requests.get(
                f'{request.host_url}api/auth/profile',
                headers=headers
            )
            if response.status_code == 200:
                user_data = response.json()
        except Exception as e:
            print(f"Error fetching user data: {e}")
    
    return {
        'user': user_data,
        'current_year': datetime.now().year,
        'app_name': 'Journey Risk Management System'
    }

# Import and register frontend routes
from frontend.routes import auth_routes, dashboard_routes, routes_routes, vehicle_routes

frontend_app.register_blueprint(auth_routes.bp)
frontend_app.register_blueprint(dashboard_routes.bp)
frontend_app.register_blueprint(routes_routes.bp)
frontend_app.register_blueprint(vehicle_routes.bp)

# Error handlers
@frontend_app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@frontend_app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

# Create a dispatcher to handle both frontend and backend
application = DispatcherMiddleware(frontend_app, {
    '/api': backend_app
})

if __name__ == '__main__':
    # Run the combined application
    run_simple('0.0.0.0', 5000, application,
               use_reloader=True,
               use_debugger=True,
               use_evalex=True)