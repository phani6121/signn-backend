"""
Firebase integration examples for the API.
Demonstrates how to use the Firestore manager in your endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.core.firebase import firestore_manager

router = APIRouter(prefix="/firebase", tags=["firebase"])


class UserData(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None


@router.post("/users", response_model=UserResponse)
async def create_user(user_id: str, user: UserData):
    """
    Create a new user document in Firestore.
    
    Example:
        POST /api/v1/firebase/users?user_id=user123
        {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1234567890"
        }
    """
    try:
        data = user.dict()
        firestore_manager.create_document("users", user_id, data)
        return UserResponse(id=user_id, **data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """
    Retrieve a user document from Firestore.
    
    Example:
        GET /api/v1/firebase/users/user123
    """
    try:
        doc = firestore_manager.get_document("users", user_id)
        if not doc:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse(id=user_id, **doc)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user: UserData):
    """
    Update a user document in Firestore.
    
    Example:
        PUT /api/v1/firebase/users/user123
        {
            "name": "Jane Doe",
            "email": "jane@example.com"
        }
    """
    try:
        data = user.dict()
        firestore_manager.update_document("users", user_id, data)
        return UserResponse(id=user_id, **data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    """
    Delete a user document from Firestore.
    
    Example:
        DELETE /api/v1/firebase/users/user123
    """
    try:
        firestore_manager.delete_document("users", user_id)
        return {"message": f"User {user_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users", response_model=List[UserResponse])
async def list_users(limit: int = 100):
    """
    List all users from Firestore.
    
    Example:
        GET /api/v1/firebase/users?limit=50
    """
    try:
        docs = firestore_manager.query_documents("users", limit=limit)
        # Note: You'll need to enhance this to include user IDs from doc metadata
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/health")
async def health_check():
    """
    Check Firebase connection health.
    
    Example:
        POST /api/v1/firebase/health
    """
    try:
        from app.services.firebaseservice import get_firestore_client
        db = get_firestore_client()
        collections = list(db.collections())
        return {
            "status": "healthy",
            "firebase": "connected",
            "collections_count": len(collections),
            "collections": [c.id for c in collections]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"status": "unhealthy", "error": str(e)})
