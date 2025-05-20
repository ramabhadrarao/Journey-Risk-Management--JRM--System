from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import requests
import json
from datetime import datetime, timedelta
from functools import wraps

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@login_required
def index():
    """Main dashboard page"""
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    try:
        # Get dashboard summary
        response = requests.get(
            f'{request.host_url}api/dashboard/summary',
            headers=headers
        )
        
        if response.status_code == 200:
            dashboard_data = response.json()
            
            # Get real-time updates
            updates_response = requests.get(
                f'{request.host_url}api/dashboard/real-time-updates',
                headers=headers
            )
            
            real_time_data = {}
            if updates_response.status_code == 200:
                real_time_data = updates_response.json()
            
            return render_template(
                'dashboard/index.html',
                dashboard_data=dashboard_data,
                real_time_data=real_time_data
            )
        else:
            flash('Failed to load dashboard data', 'danger')
            return render_template('dashboard/index.html', dashboard_data={}, real_time_data={})
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return render_template('dashboard/index.html', dashboard_data={}, real_time_data={})

@bp.route('/risk-analysis')
@login_required
def risk_analysis():
    """Risk analysis dashboard page"""
    # This page will load the Dash app via iframe
    return render_template('dashboard/risk_analysis.html')

@bp.route('/vehicle-analysis')
@login_required
def vehicle_analysis():
    """Vehicle analysis dashboard page"""
    # This page will load the Dash app via iframe
    return render_template('dashboard/vehicle_analysis.html')

@bp.route('/route-comparison', methods=['GET', 'POST'])
@login_required
def route_comparison():
    """Route comparison page"""
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    if request.method == 'POST':
        route_ids = request.form.getlist('route_ids')
        
        if not route_ids:
            flash('Please select at least one route to compare', 'warning')
            return redirect(url_for('routes.list_routes'))
        
        try:
            response = requests.post(
                f'{request.host_url}api/dashboard/route-comparison',
                headers=headers,
                json={'route_ids': route_ids}
            )
            
            if response.status_code == 200:
                comparison_data = response.json()
                return render_template(
                    'dashboard/route_comparison.html',
                    comparison_data=comparison_data
                )
            else:
                flash('Failed to load comparison data', 'danger')
                return redirect(url_for('routes.list_routes'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('routes.list_routes'))
    
    # GET request - get routes first
    try:
        response = requests.get(
            f'{request.host_url}api/routes/',
            headers=headers
        )
        
        if response.status_code == 200:
            routes_data = response.json()
            return render_template(
                'dashboard/route_comparison_select.html',
                routes=routes_data['routes']
            )
        else:
            flash('Failed to load routes data', 'danger')
            return redirect(url_for('dashboard.index'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('dashboard.index'))

@bp.route('/api/dashboard-data')
@login_required
def dashboard_data():
    """API endpoint to get dashboard data for AJAX requests"""
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    try:
        # Get dashboard summary
        response = requests.get(
            f'{request.host_url}api/dashboard/summary',
            headers=headers
        )
        
        if response.status_code == 200:
            dashboard_data = response.json()
            return jsonify(dashboard_data)
        else:
            return jsonify({"error": "Failed to load dashboard data"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/api/real-time-updates')
@login_required
def real_time_updates():
    """API endpoint to get real-time updates for AJAX requests"""
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    try:
        response = requests.get(
            f'{request.host_url}api/dashboard/real-time-updates',
            headers=headers
        )
        
        if response.status_code == 200:
            updates_data = response.json()
            return jsonify(updates_data)
        else:
            return jsonify({"error": "Failed to load real-time updates"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500