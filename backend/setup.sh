#!/bin/bash
# setup.sh - Script to set up the JRM System environment

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating required directories..."
mkdir -p logs
mkdir -p ml_models/accident_risk ml_models/breakdown_prediction ml_models/eta_optimization ml_models/route_safety ml_models/weather_hazard

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from sample..."
    cp .env.sample .env
    echo "Please edit .env file with your configuration settings."
fi

# Check MongoDB connection
echo "Checking MongoDB connection..."
python -c "import pymongo; pymongo.MongoClient('mongodb://localhost:27017/').server_info()" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Warning: Could not connect to MongoDB. Please make sure MongoDB is running."
else
    echo "MongoDB connection successful."
fi

# Check Redis connection
echo "Checking Redis connection..."
python -c "import redis; redis.Redis(host='localhost', port=6379).ping()" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Warning: Could not connect to Redis. Please make sure Redis is running."
else
    echo "Redis connection successful."
fi

echo "Setup complete! Run the application with: python run.py"