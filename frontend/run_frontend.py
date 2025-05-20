# run_frontend.py
import os
import sys

# Add the current directory to Python path to make frontend importable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Create a mock backend module to satisfy the import
import types
sys.modules['backend'] = types.ModuleType('backend')
sys.modules['backend.app'] = types.ModuleType('backend.app')
sys.modules['backend.app'].app = None  # Mock the app object

# Import and run the frontend app
from frontend.app import frontend_app
from werkzeug.serving import run_simple

if __name__ == "__main__":
    # Run the frontend app on port 8000
    run_simple('0.0.0.0', 8000, frontend_app, use_reloader=True, use_debugger=True)