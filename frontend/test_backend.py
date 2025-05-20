#!/usr/bin/env python
"""
Test script to verify connectivity between frontend and backend
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get backend URL from environment or use default
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')

def test_backend_connection():
    """Test basic connectivity to the backend"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/auth/profile", timeout=5)
        print(f"Backend connection: {'SUCCESS' if response.status_code == 401 else 'FAILED'}")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text[:100]}...")
        return True
    except requests.exceptions.ConnectionError:
        print(f"Backend connection: FAILED - Could not connect to {BACKEND_URL}")
        return False
    except Exception as e:
        print(f"Backend connection: FAILED - {str(e)}")
        return False

def test_login(email_or_username, password):
    """Test login with provided credentials"""
    # Determine if input is email or username
    if '@' in email_or_username:
        data = {
            'email': email_or_username,
            'password': password
        }
    else:
        data = {
            'username': email_or_username,
            'password': password
        }
    
    try:
        print(f"Testing login with data: {json.dumps(data)}")
        response = requests.post(
            f"{BACKEND_URL}/api/auth/login",
            json=data,
            timeout=5
        )
        
        print(f"Login test: {'SUCCESS' if response.status_code == 200 else 'FAILED'}")
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"User ID: {result.get('user', {}).get('id')}")
            print(f"Username: {result.get('user', {}).get('username')}")
            print(f"Role: {result.get('user', {}).get('role')}")
            print("Access token received: Yes")
            print("Refresh token received: Yes")
        else:
            print(f"Response: {response.text}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"Login test: FAILED - {str(e)}")
        return False

if __name__ == "__main__":
    print("============================================")
    print("  Backend Connectivity Test Tool")
    print("============================================")
    print(f"Backend URL: {BACKEND_URL}")
    print("--------------------------------------------")
    
    # Test backend connection
    if test_backend_connection():
        # If connection successful, test login
        print("\nTesting login credentials...")
        print("--------------------------------------------")
        
        # Test common credentials
        credentials = [
            ("admin", "admin123"),
            ("test@example.com", "Password123!"),
            ("testuser", "testpassword")
        ]
        
        success = False
        for username, password in credentials:
            print(f"\nTrying credentials: {username} / {password}")
            if test_login(username, password):
                success = True
                break
        
        if not success:
            print("\nWould you like to try custom credentials? (y/n)")
            choice = input("> ")
            if choice.lower() == 'y':
                email_or_username = input("Enter email or username: ")
                password = input("Enter password: ")
                test_login(email_or_username, password)
    
    print("\n============================================")
    print("  Test Complete")
    print("============================================")