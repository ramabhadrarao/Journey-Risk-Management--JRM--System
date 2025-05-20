from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import requests
import json
from datetime import datetime
from functools import wraps

bp = Blueprint('vehicles', __name__, url_prefix='/vehicles')

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
def list_vehicles():
    """List all vehicles"""
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    try:
        response = requests.get(
            f'{request.host_url}api/vehicles/',
            headers=headers
        )
        
        if response.status_code == 200:
            vehicles_data = response.json()
            return render_template(
                'vehicles/list.html',
                vehicles=vehicles_data['vehicles']
            )
        else:
            flash('Failed to load vehicles data', 'danger')
            return render_template('vehicles/list.html', vehicles=[])
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return render_template('vehicles/list.html', vehicles=[])

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_vehicle():
    """Create a new vehicle"""
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'type': request.form.get('type'),
            'make': request.form.get('make'),
            'model': request.form.get('model'),
            'year': request.form.get('year'),
            'registration': request.form.get('registration'),
            'fuel_type': request.form.get('fuel_type'),
            'tank_capacity': request.form.get('tank_capacity'),
            'average_mileage': request.form.get('average_mileage'),
            'last_service_date': request.form.get('last_service_date'),
            'next_service_date': request.form.get('next_service_date'),
            'last_service_mileage': request.form.get('last_service_mileage')
        }
        
        try:
            response = requests.post(
                f'{request.host_url}api/vehicles/',
                headers=headers,
                json=data
            )
            
            if response.status_code == 201:
                result = response.json()
                flash('Vehicle created successfully', 'success')
                return redirect(url_for('vehicles.view_vehicle', vehicle_id=result['vehicle']['_id']))
            else:
                error_msg = response.json().get('error', 'Failed to create vehicle')
                flash(error_msg, 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('vehicles/create.html')

@bp.route('/<vehicle_id>')
@login_required
def view_vehicle(vehicle_id):
    """View vehicle details"""
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    try:
        response = requests.get(
            f'{request.host_url}api/vehicles/{vehicle_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            vehicle_data = response.json()
            
            # Get telemetry data
            telemetry_response = requests.get(
                f'{request.host_url}api/vehicles/{vehicle_id}/telemetry',
                headers=headers
            )
            
            telemetry_data = {}
            if telemetry_response.status_code == 200:
                telemetry_data = telemetry_response.json()
            
            return render_template(
                'vehicles/view.html',
                vehicle=vehicle_data['vehicle'],
                telemetry=telemetry_data
            )
        else:
            error_msg = response.json().get('error', 'Failed to load vehicle')
            flash(error_msg, 'danger')
            return redirect(url_for('vehicles.list_vehicles'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('vehicles.list_vehicles'))

@bp.route('/<vehicle_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_vehicle(vehicle_id):
    """Edit vehicle details"""
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'type': request.form.get('type'),
            'make': request.form.get('make'),
            'model': request.form.get('model'),
            'year': request.form.get('year'),
            'registration': request.form.get('registration'),
            'fuel_type': request.form.get('fuel_type'),
            'tank_capacity': request.form.get('tank_capacity'),
            'average_mileage': request.form.get('average_mileage'),
            'last_service_date': request.form.get('last_service_date'),
            'next_service_date': request.form.get('next_service_date'),
            'last_service_mileage': request.form.get('last_service_mileage')
        }
        
        try:
            response = requests.put(
                f'{request.host_url}api/vehicles/{vehicle_id}',
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                flash('Vehicle updated successfully', 'success')
                return redirect(url_for('vehicles.view_vehicle', vehicle_id=vehicle_id))
            else:
                error_msg = response.json().get('error', 'Failed to update vehicle')
                flash(error_msg, 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    # GET request or form submission failed - load current vehicle data
    try:
        response = requests.get(
            f'{request.host_url}api/vehicles/{vehicle_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            vehicle_data = response.json()
            return render_template('vehicles/edit.html', vehicle=vehicle_data['vehicle'])
        else:
            error_msg = response.json().get('error', 'Failed to load vehicle')
            flash(error_msg, 'danger')
            return redirect(url_for('vehicles.list_vehicles'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('vehicles.list_vehicles'))

@bp.route('/<vehicle_id>/delete', methods=['POST'])
@login_required
def delete_vehicle(vehicle_id):
    """Delete a vehicle"""
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    try:
        response = requests.delete(
            f'{request.host_url}api/vehicles/{vehicle_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            flash('Vehicle deleted successfully', 'success')
        else:
            error_msg = response.json().get('error', 'Failed to delete vehicle')
            flash(error_msg, 'danger')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('vehicles.list_vehicles'))

@bp.route('/<vehicle_id>/maintenance', methods=['GET', 'POST'])
@login_required
def add_maintenance(vehicle_id):
    """Add maintenance record to vehicle"""
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    if request.method == 'POST':
        data = {
            'type': request.form.get('type'),
            'date': request.form.get('date'),
            'mileage': request.form.get('mileage'),
            'description': request.form.get('description'),
            'cost': request.form.get('cost'),
            'service_center': request.form.get('service_center')
        }
        
        try:
            response = requests.post(
                f'{request.host_url}api/vehicles/{vehicle_id}/maintenance',
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                flash('Maintenance record added successfully', 'success')
            else:
                error_msg = response.json().get('error', 'Failed to add maintenance record')
                flash(error_msg, 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
        
        return redirect(url_for('vehicles.view_vehicle', vehicle_id=vehicle_id))
    
    # GET request - show form
    try:
        response = requests.get(
            f'{request.host_url}api/vehicles/{vehicle_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            vehicle_data = response.json()
            return render_template('vehicles/add_maintenance.html', vehicle=vehicle_data['vehicle'])
        else:
            error_msg = response.json().get('error', 'Failed to load vehicle')
            flash(error_msg, 'danger')
            return redirect(url_for('vehicles.list_vehicles'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('vehicles.list_vehicles'))

@bp.route('/api/vehicle-telemetry/<vehicle_id>')
@login_required
def vehicle_telemetry(vehicle_id):
    """API endpoint to get vehicle telemetry for AJAX requests"""
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    try:
        response = requests.get(
            f'{request.host_url}api/vehicles/{vehicle_id}/telemetry',
            headers=headers
        )
        
        if response.status_code == 200:
            telemetry_data = response.json()
            return jsonify(telemetry_data)
        else:
            return jsonify({"error": "Failed to load telemetry data"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500