import hashlib
import logging
from datetime import datetime
from uuid import uuid4
from typing import Optional, Dict, Any

from ..schemas.auth import LoginRequest, LoginResponse
from ..core.firebase import firestore_manager

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(stored_hash: str, provided_password: str) -> bool:
    """Verify password against stored hash"""
    return stored_hash == hash_password(provided_password)


def login(payload: LoginRequest) -> LoginResponse:
    """
    Authenticate user and update ONLY their login details in database.
    
    Args:
        payload: LoginRequest with username/email and password
        
    Returns:
        LoginResponse with token and user info
        
    Raises:
        ValueError: If user not found or password incorrect
    """
    try:
        # Try to find user by username or email
        username_or_email = payload.username or payload.email

        if not username_or_email:
            raise ValueError("Username or email is required")
        
        logger.info(f"Login attempt for: {username_or_email}")
        
        # Query users collection for the specific user by document ID first
        user_doc = firestore_manager.get_document('users', username_or_email)
        user_doc_id = username_or_email

        # If doc-id lookup fails, try field-based lookup (username/email)
        if not user_doc and payload.username:
            match = firestore_manager.get_document_by_field('users', 'username', payload.username)
            if match:
                user_doc_id = match["id"]
                user_doc = match["data"]
        if not user_doc and payload.email:
            match = firestore_manager.get_document_by_field('users', 'email', payload.email)
            if match:
                user_doc_id = match["id"]
                user_doc = match["data"]
        
        if not user_doc:
            logger.info(f"User not found, creating on first login: {username_or_email}")

            # Build a minimal user document from login payload
            email = payload.email
            username = payload.username
            name = username or (email.split("@")[0] if email else None)

            user_doc = {
                "username": username,
                "email": email,
                "password_hash": hash_password(payload.password),
                "name": name,
                "role": "driver",
                "status": "active",
                "last_login": None,
                "login_count": 0,
            }

            # Create document using provided username or email as ID
            firestore_manager.create_document("users", username_or_email, user_doc)
            user_doc_id = username_or_email
            user_doc = firestore_manager.get_document("users", user_doc_id)
        
        # Verify password
        stored_password_hash = user_doc.get('password_hash')
        if not stored_password_hash or not verify_password(stored_password_hash, payload.password):
            logger.warning(f"Invalid password for user: {username_or_email}")
            raise ValueError("Invalid username or password")
        
        # Generate token
        token = f"token_{uuid4().hex}"
        
        # Update ONLY this user's login details in database
        # Use merge upsert to ensure the document exists
        project_id = getattr(firestore_manager.db, "project", None)
        logger.info(f"Updating login for user_id={user_doc_id} on project={project_id}")
        login_update = {
            'last_login': datetime.utcnow(),
            'login_count': (user_doc.get('login_count', 0) or 0) + 1,
            'last_login_ip': None,  # Can be set from request if needed
            'token': token,
        }
        
        # Update only this specific user document (create if missing)
        firestore_manager.create_document('users', user_doc_id, login_update, merge=True)
        
        logger.info(f"Successful login for user: {username_or_email}")
        
        # Get updated user data
        updated_user = firestore_manager.get_document('users', user_doc_id)
        
        return LoginResponse(
            token=token,
            user_id=user_doc_id,
            username=updated_user.get('username'),
            email=updated_user.get('email'),
            name=updated_user.get('name'),
            role=updated_user.get('role', 'driver'),
            login_count=updated_user.get('login_count', 1),
            last_login=updated_user.get('last_login'),
        )
        
    except ValueError as e:
        logger.error(f"Login failed: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise ValueError("Login failed. Please try again.")
