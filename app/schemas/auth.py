from pydantic import BaseModel
from typing import Optional
from datetime import datetime
 
 
class LoginRequest(BaseModel):
    """Login request - accepts either username or email"""
    username: Optional[str] = None
    email: Optional[str] = None
    password: str
    language: Optional[str] = None
    user_type: Optional[str] = None
   
    class Config:
        json_schema_extra = {
            "example": {
                "username": "testuser1",
                "password": "123456",
                "language": "en",
                "user_type": "employee"
            }
        }
 
 
class LoginResponse(BaseModel):
    """Login response with user details"""
    token: str
    token_type: str = "bearer"
    user_id: str
    username: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    language: Optional[str] = None
    user_type: Optional[str] = None
    login_count: Optional[int] = None
    last_login: Optional[datetime] = None
   
    class Config:
        json_schema_extra = {
            "example": {
                "token": "token_abc123def456",
                "token_type": "bearer",
                "user_id": "testuser1",
                "username": "testuser1",
                "email": "testuser1@example.com",
                "name": "Test User 1",
                "role": "driver",
                "language": "en",
                "user_type": "employee",
                "login_count": 5,
                "last_login": "2026-02-04T10:30:00"
            }
        }
