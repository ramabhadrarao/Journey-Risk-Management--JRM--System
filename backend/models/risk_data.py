
# backend/models/risk_data.py
import datetime
from . import db

class RiskData:
    collection = db.risk_data
    
    @staticmethod
    def create(route_id):
        """Create a new risk data entry for a route"""
        risk_data = {
            'route_id': route_id,
            'created_at': datetime.datetime.utcnow(),
            'last_updated': datetime.datetime.utcnow(),
            'accident_risks': [],
            'weather_hazards': [],
            'elevation_risks': [],
            'blind_spots': [],
            'network_coverage': [],
            'eco_sensitive_zones': [],
            'nearby_facilities': {
                'hospitals': [],
                'police_stations': [],
                'fuel_stations': [],
                'rest_areas': [],
                'repair_shops': []
            },
            'overall_risk_score': None,
            'risk_level': None
        }
        
        result = db.risk_data.insert_one(risk_data)
        risk_data['_id'] = result.inserted_id
        return risk_data
    
    @staticmethod
    def get_by_route_id(route_id):
        """Get risk data by route ID"""
        return db.risk_data.find_one({'route_id': route_id})
    
    @staticmethod
    def update(route_id, data):
        """Update risk data"""
        data['last_updated'] = datetime.datetime.utcnow()
        db.risk_data.update_one(
            {'route_id': route_id},
            {'$set': data}
        )
    
    @staticmethod
    def add_risk_point(route_id, risk_type, risk_data):
        """Add a risk point to a specific risk category"""
        update_field = f'{risk_type}'
        
        return db.risk_data.update_one(
            {'route_id': route_id},
            {
                '$push': {update_field: risk_data},
                '$set': {'last_updated': datetime.datetime.utcnow()}
            }
        )
    
    @staticmethod
    def update_risk_score(route_id, overall_score, risk_level):
        """Update the overall risk score and level"""
        db.risk_data.update_one(
            {'route_id': route_id},
            {
                '$set': {
                    'overall_risk_score': overall_score,
                    'risk_level': risk_level,
                    'last_updated': datetime.datetime.utcnow()
                }
            }
        )