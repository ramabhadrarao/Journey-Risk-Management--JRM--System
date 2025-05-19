 #backend/models/vehicle.py
import datetime
from bson.objectid import ObjectId
from . import db

class Vehicle:
    collection = db.vehicles
    
    @staticmethod
    def create(user_id, data):
        """Create a new vehicle"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
            
        vehicle = {
            'user_id': user_id,
            'name': data.get('name', 'My Vehicle'),
            'type': data.get('type', 'car'),
            'make': data.get('make'),
            'model': data.get('model'),
            'year': data.get('year'),
            'registration': data.get('registration'),
            'fuel_type': data.get('fuel_type', 'petrol'),
            'tank_capacity': data.get('tank_capacity'),
            'average_mileage': data.get('average_mileage'),
            'created_at': datetime.datetime.utcnow(),
            'last_updated': datetime.datetime.utcnow(),
            'maintenance': {
                'last_service_date': data.get('last_service_date'),
                'next_service_date': data.get('next_service_date'),
                'last_service_mileage': data.get('last_service_mileage'),
                'history': []
            }
        }
        
        result = db.vehicles.insert_one(vehicle)
        vehicle['_id'] = result.inserted_id
        return vehicle
    
    @staticmethod
    def get_by_id(vehicle_id):
        """Get vehicle by ID"""
        if isinstance(vehicle_id, str):
            vehicle_id = ObjectId(vehicle_id)
        return db.vehicles.find_one({'_id': vehicle_id})
    
    @staticmethod
    def get_by_user(user_id):
        """Get vehicles by user ID"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        return list(db.vehicles.find({'user_id': user_id}))
    
    @staticmethod
    def update(vehicle_id, data):
        """Update vehicle data"""
        if isinstance(vehicle_id, str):
            vehicle_id = ObjectId(vehicle_id)
            
        data['last_updated'] = datetime.datetime.utcnow()
        
        db.vehicles.update_one(
            {'_id': vehicle_id},
            {'$set': data}
        )
        
        return db.vehicles.find_one({'_id': vehicle_id})
    
    @staticmethod
    def add_maintenance_record(vehicle_id, record):
        """Add a maintenance record"""
        if isinstance(vehicle_id, str):
            vehicle_id = ObjectId(vehicle_id)
            
        record['date'] = record.get('date', datetime.datetime.utcnow())
        
        db.vehicles.update_one(
            {'_id': vehicle_id},
            {
                '$push': {'maintenance.history': record},
                '$set': {
                    'last_updated': datetime.datetime.utcnow(),
                    'maintenance.last_service_date': record.get('date'),
                    'maintenance.last_service_mileage': record.get('mileage')
                }
            }
        )
        
        return db.vehicles.find_one({'_id': vehicle_id})
    
    @staticmethod
    def delete(vehicle_id):
        """Delete a vehicle"""
        if isinstance(vehicle_id, str):
            vehicle_id = ObjectId(vehicle_id)
        return db.vehicles.delete_one({'_id': vehicle_id})