from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import requests
import json
from datetime import datetime
from functools import wraps

bp = Blueprint('routes', __name__, url_prefix='/routes')

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
def list_routes():
    """List all routes"""
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    # Get page from query params
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    try:
        response = requests.get(
            f'{request.host_url}api/routes/',
            headers=headers,
            params={'page': page, 'per_page': per_page}
        )
        
        if response.status_code == 200:
            routes_data = response.json()
            return render_template(
                'routes/list.html',
                routes=routes_data['routes'],
                total=routes_data['total'],
                page=routes_data['page'],
                per_page=routes_data['per_page'],
                total_pages=routes_data['total_pages']
            )
        else:
            flash('Failed to load routes data', 'danger')
            return render_template('routes/list.html', routes=[], total=0, page=1, per_page=10, total_pages=0)
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return render_template('routes/list.html', routes=[], total=0, page=1, per_page=10, total_pages=0)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_route():
    """Create a new route"""
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    # If POST request, process form data
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'origin': {
                'address': request.form.get('origin_address'),
            },
            'destination': {
                'address': request.form.get('destination_address'),
            },
            'vehicle_id': request.form.get('vehicle_id')
        }
        
        try:
            response = requests.post(
                f'{request.host_url}api/routes/',
                headers=headers,
                json=data
            )
            
            if response.status_code == 201:
                result = response.json()
                flash('Route created successfully, processing started', 'success')
                return redirect(url_for('routes.view_route', route_id=result['route']['route_id']))
            else:
                error_msg = response.json().get('error', 'Failed to create route')
                flash(error_msg, 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    # GET request or form submission failed - load vehicles for selection
    try:
        vehicles_response = requests.get(
            f'{request.host_url}api/vehicles/',
            headers=headers
        )
        
        vehicles = []
        if vehicles_response.status_code == 200:
            vehicles = vehicles_response.json()['vehicles']
        
        return render_template('routes/create.html', vehicles=vehicles)
    except Exception as e:
        flash(f'Error loading vehicles: {str(e)}', 'danger')
        return render_template('routes/create.html', vehicles=[])

@bp.route('/<route_id>')
@login_required
def view_route(route_id):
    """View route details"""
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    try:
        response = requests.get(
            f'{request.host_url}api/routes/{route_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            route_data = response.json()
            return render_template(
                'routes/view.html',
                route=route_data['route'],
                risk_data=route_data['risk_data']
            )
        else:
            error_msg = response.json().get('error', 'Failed to load route')
            flash(error_msg, 'danger')
            return redirect(url_for('routes.list_routes'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('routes.list_routes'))

@bp.route('/<route_id>/delete', methods=['POST'])
@login_required
def delete_route(route_id):
    """Delete a route"""
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    try:
        response = requests.delete(
            f'{request.host_url}api/routes/{route_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            flash('Route deleted successfully', 'success')
        else:
            error_msg = response.json().get('error', 'Failed to delete route')
            flash(error_msg, 'danger')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('routes.list_routes'))

@bp.route('/<route_id>/regenerate', methods=['POST'])
@login_required
def regenerate_route(route_id):
    """Regenerate route analysis"""
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    try:
        response = requests.post(
            f'{request.host_url}api/routes/{route_id}/regenerate',
            headers=headers
        )
        
        if response.status_code == 200:
            flash('Route regeneration started', 'success')
        else:
            error_msg = response.json().get('error', 'Failed to regenerate route')
            flash(error_msg, 'danger')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('routes.view_route', route_id=route_id))

@bp.route('/api/route-status/<route_id>')
@login_required
def route_status(route_id):
    """API endpoint to get route status for AJAX requests"""
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    try:
        response = requests.get(
            f'{request.host_url}api/routes/{route_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            route_data = response.json()
            return jsonify({
                'status': route_data['route']['status'],
                'risk_score': route_data['route'].get('risk_score'),
                'risk_level': route_data['route'].get('risk_level')
            })
        else:
            return jsonify({"error": "Failed to load route status"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500