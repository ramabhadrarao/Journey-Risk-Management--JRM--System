from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import requests
import json
from datetime import datetime

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        data = {
            'username': request.form.get('username'),
            'password': request.form.get('password')
        }
        
        try:
            response = requests.post(
                f'{request.host_url}api/auth/login',
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                session['access_token'] = result['access_token']
                session['refresh_token'] = result['refresh_token']
                session['user_id'] = result['user']['id']
                
                flash('Login successful', 'success')
                return redirect(url_for('dashboard.index'))
            else:
                error_msg = response.json().get('error', 'Login failed')
                flash(error_msg, 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
        
    return render_template('auth/login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration"""
    if request.method == 'POST':
        data = {
            'username': request.form.get('username'),
            'email': request.form.get('email'),
            'password': request.form.get('password'),
            'company': request.form.get('company')
        }
        
        try:
            response = requests.post(
                f'{request.host_url}api/auth/register',
                json=data
            )
            
            if response.status_code == 201:
                result = response.json()
                session['access_token'] = result['access_token']
                session['refresh_token'] = result['refresh_token']
                session['user_id'] = result['user']['id']
                
                flash('Registration successful', 'success')
                return redirect(url_for('dashboard.index'))
            else:
                error_msg = response.json().get('error', 'Registration failed')
                flash(error_msg, 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('auth/register.html')

@bp.route('/logout')
def logout():
    """Handle user logout"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/profile', methods=['GET', 'POST'])
def profile():
    """Handle user profile view/edit"""
    if 'access_token' not in session:
        return redirect(url_for('auth.login'))
    
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    if request.method == 'POST':
        data = {
            'email': request.form.get('email'),
            'company': request.form.get('company'),
            'preferences': {
                'notifications': {
                    'email': request.form.get('notify_email') == 'on',
                    'sms': request.form.get('notify_sms') == 'on',
                    'push': request.form.get('notify_push') == 'on'
                },
                'dashboard': {
                    'default_view': request.form.get('default_view'),
                    'risk_threshold': request.form.get('risk_threshold')
                }
            }
        }
        
        try:
            response = requests.put(
                f'{request.host_url}api/auth/profile',
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                flash('Profile updated successfully', 'success')
            else:
                error_msg = response.json().get('error', 'Update failed')
                flash(error_msg, 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    # Get current profile
    try:
        response = requests.get(
            f'{request.host_url}api/auth/profile',
            headers=headers
        )
        
        if response.status_code == 200:
            user_data = response.json()
            return render_template('auth/profile.html', user=user_data)
        else:
            flash('Failed to load profile data', 'danger')
            return redirect(url_for('dashboard.index'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('dashboard.index'))

@bp.route('/change-password', methods=['POST'])
def change_password():
    """Handle password change"""
    if 'access_token' not in session:
        return redirect(url_for('auth.login'))
    
    data = {
        'current_password': request.form.get('current_password'),
        'new_password': request.form.get('new_password')
    }
    
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    
    try:
        response = requests.post(
            f'{request.host_url}api/auth/change-password',
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            flash('Password changed successfully', 'success')
        else:
            error_msg = response.json().get('error', 'Password change failed')
            flash(error_msg, 'danger')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('auth.profile'))

@bp.route('/refresh-token', methods=['POST'])
def refresh_token():
    """Refresh the access token"""
    if 'refresh_token' not in session:
        return jsonify({"error": "No refresh token"}), 401
    
    headers = {'Authorization': f'Bearer {session["refresh_token"]}'}
    
    try:
        response = requests.post(
            f'{request.host_url}api/auth/refresh',
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            session['access_token'] = result['access_token']
            return jsonify({"message": "Token refreshed"}), 200
        else:
            # If refresh fails, redirect to login
            session.clear()
            return jsonify({"error": "Session expired"}), 401
    except Exception as e:
        session.clear()
        return jsonify({"error": str(e)}), 500