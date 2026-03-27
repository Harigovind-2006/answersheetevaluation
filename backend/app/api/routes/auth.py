from fastapi import APIRouter, HTTPException, status
from loguru import logger

from ...models.schemas import LoginRequest, AuthResponse
from ...core.supabase import supabase

router = APIRouter(tags=["auth"])

@router.post("/login", response_model=AuthResponse, summary="Login using Supabase")
async def login(credentials: LoginRequest):
    """
    Authenticate a user via Supabase using email and password.
    Returns an access token and user details.
    """
    try:
        # Supabase Python client authentication
        logger.info(f"Attempting login for user: {credentials.email}")
        response = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password,
        })
        
        # Check if the response contains the expected session data
        if not response.session or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
            
        return AuthResponse(
            access_token=response.session.access_token,
            user_id=response.user.id,
            email=response.user.email
        )
        
    except Exception as e:
        logger.error(f"Login failed: {e}")
        # Standardize error message for frontend
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )


@router.post("/register", response_model=AuthResponse, summary="Register using Supabase")
async def register(credentials: LoginRequest):
    """
    Register a user via Supabase using email and password.
    Returns an access token and user details.
    """
    try:
        logger.info(f"Attempting registration for user: {credentials.email}")
        response = supabase.auth.sign_up({
            "email": credentials.email,
            "password": credentials.password,
        })
        
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed, user not created."
            )
            
        return AuthResponse(
            access_token=response.session.access_token if response.session else "",
            user_id=response.user.id,
            email=response.user.email
        )
        
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        # Supabase Python client might throw AuthApiError
        msg = str(e)
        if hasattr(e, 'message'):
            msg = e.message
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )
