"""
Authentication Routes

Login, logout, and user management endpoints.

Task Reference: Phase 3, Task 3.4
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from ..middleware.auth import auth_service, get_current_user
import logging


router = APIRouter()
logger = logging.getLogger(__name__)


# Request/Response Models
class LoginRequest(BaseModel):
    """Login request model"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=3)


class RegisterRequest(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = Field(None, max_length=100)


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    """User information response"""
    id: int
    username: str
    email: str
    full_name: Optional[str]


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Login endpoint

    **Request**:
    ```json
    {
        "username": "admin",
        "password": "admin123"
    }
    ```

    **Response**:
    ```json
    {
        "access_token": "eyJhbGci...",
        "token_type": "bearer",
        "user": {
            "id": 1,
            "username": "admin",
            "email": "admin@kms.local",
            "full_name": "Admin User"
        }
    }
    ```

    **Usage**:
    Use the access token in subsequent requests:
    ```
    Authorization: Bearer eyJhbGci...
    ```
    """
    # Authenticate user
    user = auth_service.authenticate(request.username, request.password)

    if not user:
        logger.warning(f"Failed login attempt for user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    # Create access token
    access_token = auth_service.create_access_token(user)

    logger.info(f"User logged in: {user['username']}")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """
    Register new user

    **Request**:
    ```json
    {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "securepassword",
        "full_name": "New User"
    }
    ```

    **Response**:
    ```json
    {
        "id": 4,
        "username": "newuser",
        "email": "newuser@example.com",
        "full_name": "New User"
    }
    ```
    """
    try:
        user = auth_service.create_user(
            username=request.username,
            email=request.email,
            password=request.password,
            full_name=request.full_name
        )

        logger.info(f"New user registered: {user['username']}")

        return user

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """
    Get current authenticated user information

    Requires authentication (Bearer token).

    **Response**:
    ```json
    {
        "id": 1,
        "username": "admin",
        "email": "admin@kms.local",
        "full_name": "Admin User"
    }
    ```
    """
    return user


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """
    Logout current user

    Note: In this simple implementation, tokens remain valid until expiry.
    For production, implement token revocation.
    """
    logger.info(f"User logged out: {user['username']}")

    return {"message": "Logged out successfully"}
