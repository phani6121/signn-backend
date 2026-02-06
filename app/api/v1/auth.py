from typing import Dict

from fastapi import APIRouter, HTTPException

from ...schemas.auth import LoginRequest, LoginResponse
from ...services.authservice import login
from ...services.shiftservice import scans, shifts, utc_now_iso

router = APIRouter()


@router.post("/auth/login", response_model=LoginResponse)
def login_route(payload: LoginRequest) -> LoginResponse:
    """
    Login endpoint that accepts username or email with password.
    Updates ONLY the specific user's login information in the database.
    
    Example:
        POST /api/auth/login
        {
            "username": "testuser1",
            "password": "123456"
        }
    
    Or with email:
        POST /api/auth/login
        {
            "email": "testuser1@example.com",
            "password": "123456"
        }
    """
    try:
        return login(payload)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Login failed. Please try again.")


@router.get("/user/dashboard")
def user_dashboard() -> Dict[str, object]:
    return {
        "active_shifts": len(shifts),
        "open_scans": len(scans),
        "last_updated": utc_now_iso(),
    }
