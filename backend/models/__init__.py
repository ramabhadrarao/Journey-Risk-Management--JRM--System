# backend/models/__init__.py
# This file initializes the database connection to be used by the models

from flask_pymongo import PyMongo

# Initialize mongo to None and set it up later when the app is available
mongo = None
db = None

def init_db(app):
    """Initialize database connection with the Flask app context"""
    global mongo, db
    mongo = PyMongo(app)
    db = mongo.db
    return db