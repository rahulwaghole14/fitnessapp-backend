import os
import logging
import firebase_admin
from firebase_admin import credentials

logger = logging.getLogger(__name__)

def initialize_firebase():
    """
    Initializes the Firebase Admin SDK safely using environment variables.
    Ensures the application is initialized exactly once.
    """
    if not firebase_admin._apps:
        try:
            project_id = os.getenv("FIREBASE_PROJECT_ID")
            private_key = os.getenv("FIREBASE_PRIVATE_KEY")
            client_email = os.getenv("FIREBASE_CLIENT_EMAIL")
            
            if not all([project_id, private_key, client_email]):
                logger.warning("Firebase credentials missing in environment variables. FCM won't work.")
                return None
                
            # Replace escaped newlines if they were loaded literally
            private_key_cleaned = private_key.replace("\\n", "\n").strip('"')
            
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": project_id,
                "private_key": private_key_cleaned,
                "client_email": client_email,
                "token_uri": "https://oauth2.googleapis.com/token"
            })
            
            app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK successfully initialized.")
            return app
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
            return None
    else:
        return firebase_admin.get_app()
