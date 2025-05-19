# backend/models/__init__.py
from flask_pymongo import PyMongo
from flask import current_app

mongo = PyMongo(current_app)
db = mongo.db

