# backend/models/route.py
import datetime
import uuid
from . import db
from bson.objectid import ObjectId

class Route:
    collection = db.routes
    
    @staticmethod
    def create(user_id, origin, destination, vehicle_id=None, name=None):
        """Create a new route"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
            
        route = {
            'route_id': str(uuid.uuid4()),
            'user_id': user_id,
            'name': name or f"Route from {origin['address']} to {destination['address']}",
            'origin': origin,
            'destination': destination,
            'vehicle_id': vehicle_id,
            'created_at': datetime.datetime.utcnow(),
            'last_updated': datetime.datetime.utcnow(),
            'status': 'processing',
            'polyline': None,
            'distance': None,
            'duration': None,
            'optimized_duration': None,
            'risk_score': None,
            'risk_level': None,
            'risks': [],
            'waypoints': []
        }
        
        result = db.routes.insert_one(route)
        route['_id'] = result.inserted_id
        return route
    
    @staticmethod
    def get_by_id(route_id):
        """Get route by ID"""
        return db.routes.find_one({'route_id': route_id})
    
    @staticmethod
    def get_by_user(user_id, limit=10, skip=0):
        """Get routes by user ID"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
            
        cursor = db.routes.find({'user_id': user_id}).sort(
            'created_at', -1
        ).skip(skip).limit(limit)
        
        return list(cursor)
    
    @staticmethod
    def update_status(route_id, status):
        """Update route status"""
        db.routes.update_one(
            {'route_id': route_id},
            {'$set': {
                'status': status,
                'last_updated': datetime.datetime.utcnow()
            }}
        )
    
    @staticmethod
    def update_route_details(route_id, details):
        """Update route details"""
        details['last_updated'] = datetime.datetime.utcnow()
        db.routes.update_one(
            {'route_id': route_id},
            {'$set': details}
        )
    
    @staticmethod
    def delete(route_id):
        """Delete a route"""
        return db.routes.delete_one({'route_id': route_id})