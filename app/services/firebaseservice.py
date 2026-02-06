"""
Firebase service for backend operations.
Handles initialization and connection to Firestore database.
"""

import json
import logging
from typing import Optional, Any
import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
# Note: On Railway, system environment variables take precedence over .env files.
env_path = Path(__file__).resolve().parents[2] / ".env.local"
load_dotenv(dotenv_path=env_path, override=False)

# Global Firebase app and Firestore client
_firebase_app: Optional[firebase_admin.App] = None
_firestore_client: Optional[Any] = None


def initialize_firebase() -> firebase_admin.App:
    """
    Initialize Firebase Admin SDK with service account credentials.
    Includes a critical fix for the 'Invalid JWT Signature' error caused by 
    malformed private key newlines in cloud environments like Railway.
    """
    global _firebase_app
    
    if _firebase_app is not None:
        return _firebase_app
    
    # Get service account key from environment
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
    
    if not service_account_json:
        logger.error("FIREBASE_SERVICE_ACCOUNT_KEY not found in environment variables.")
        raise ValueError(
            "FIREBASE_SERVICE_ACCOUNT_KEY environment variable not found. "
            "Ensure it is added to your Railway Variables tab."
        )
    
    try:
        # Parse the JSON string
        service_account = json.loads(service_account_json)
        
        # --- THE JWT SIGNATURE FIX ---
        # Railway and other providers often escape newlines. 
        # We must convert literal '\n' strings back into real newline characters.
        if "private_key" in service_account:
            service_account["private_key"] = service_account["private_key"].replace('\\n', '\n').strip()
        # -----------------------------

        # Initialize Firebase with the cleaned service account dictionary
        cred = credentials.Certificate(service_account)
        _firebase_app = firebase_admin.initialize_app(cred)
        
        logger.info(f"Firebase successfully initialized for project: {service_account.get('project_id')}")
        return _firebase_app
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse FIREBASE_SERVICE_ACCOUNT_KEY JSON: {e}")
        raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY is not valid JSON format.") from e
    except Exception as e:
        logger.error(f"Unexpected error during Firebase initialization: {e}")
        raise


def get_firestore_client() -> Any:
    """
    Get or create the Firestore client.
    """
    global _firestore_client
    
    if _firestore_client is not None:
        return _firestore_client
    
    # Ensure Firebase is initialized before requesting the client
    initialize_firebase()
    
    _firestore_client = firestore.client()
    logger.info("Firestore client initialized successfully.")
    return _firestore_client


def close_firebase() -> None:
    """
    Close the Firebase connection and reset global instances.
    """
    global _firebase_app, _firestore_client
    
    if _firebase_app is not None:
        firebase_admin.delete_app(_firebase_app)
        _firebase_app = None
        _firestore_client = None
        logger.info("Firebase connection closed.")


# Auto-initialize Firebase on module import for immediate connectivity
try:
    initialize_firebase()
except Exception as e:
    logger.warning(f"Firebase was not initialized at startup, will retry on first request: {e}")