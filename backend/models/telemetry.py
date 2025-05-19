# backend/models/telemetry.py
import datetime
from bson.objectid import ObjectId
from . import db

class Telemetry:
    collection = db.telemetry
    
    @staticmethod
    def add_record(vehicle_id, route_id, data):
        """Add a telemetry record"""
        if isinstance(vehicle_id, str) and vehicle_id != 'None':
            vehicle_id = ObjectId(vehicle_id)
        
        record = {
            'vehicle_id': vehicle_id,
            'route_id': route_id,
            'timestamp': datetime.datetime.utcnow(),
            'location': data.get('location', {}),
            'speed': data.get('speed'),
            'fuel_level': data.get('fuel_level'),
            'engine_temp': data.get('engine_temp'),
            'oil_pressure': data.get('oil_pressure'),
            'rpm': data.get('rpm'),
            'battery_voltage': data.get('battery_voltage'),
            'tire_pressure': data.get('tire_pressure', {}),
            'acceleration': data.get('acceleration', {}),
            'weather': data.get('weather', {}),
            'traffic': data.get('traffic', {})
        }
        
        result = db.telemetry.insert_one(record)
        record['_id'] = result.inserted_id
        
        return record
    
    @staticmethod
    def get_by_vehicle(vehicle_id, limit=100, skip=0):
        """Get telemetry data by vehicle ID"""
        if isinstance(vehicle_id, str):
            vehicle_id = ObjectId(vehicle_id)
            
        cursor = db.telemetry.find({'vehicle_id': vehicle_id}).sort(
            'timestamp', -1
        ).skip(skip).limit(limit)
        
        return list(cursor)
    
    @staticmethod
    def get_by_route(route_id, limit=1000):
        """Get telemetry data by route ID"""
        cursor = db.telemetry.find({'route_id': route_id}).sort(
            'timestamp', 1
        ).limit(limit)
        
        return list(cursor)
    
    @staticmethod
    def get_latest_by_vehicle(vehicle_id):
        """Get latest telemetry record for a vehicle"""
        if isinstance(vehicle_id, str):
            vehicle_id = ObjectId(vehicle_id)
            
        return db.telemetry.find_one(
            {'vehicle_id': vehicle_id},
            sort=[('timestamp', -1)]
        )