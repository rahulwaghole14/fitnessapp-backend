from sqlalchemy.orm import Session
from app.models.subscription_plans import Plan
# from app.models.payment import Payment, PaymentHistory
from datetime import date, datetime
import json

def convert_features_to_json(features):
    """Convert features (list or dict) to JSON string for database storage"""
    if features is None:
        return None
    if isinstance(features, list):
        return json.dumps(features)
    if isinstance(features, dict):
        return json.dumps(features)
    return str(features)

def convert_features_from_json(features_json):
    """Convert JSON string from database to appropriate format"""
    if features_json is None:
        return None
    try:
        parsed = json.loads(features_json)
        return parsed
    except (json.JSONDecodeError, TypeError):
        return features_json
