#!/usr/bin/env python
"""
This is the final fixed version of the run.py script.
It properly handles the initialization of the Flask app and database.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import app directly (we're already in the backend directory)
from app import app, socketio, init_scheduler

if __name__ == '__main__':
    try:
        # Initialize the scheduler for background tasks
        init_scheduler()
        
        # Get port from environment or use default
        port = int(os.environ.get('PORT', 5000))
        
        # Debug mode from environment or default to False in production
        debug = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')
        
        print(f"Starting JRM System on port {port} with debug={debug}")
        
        # Run the app with Socket.IO
        socketio.run(
            app,
            host='0.0.0.0',
            port=port,
            debug=debug,
            use_reloader=debug
        )
    except Exception as e:
        print(f"Error starting application: {str(e)}")
        import traceback
        traceback.print_exc()