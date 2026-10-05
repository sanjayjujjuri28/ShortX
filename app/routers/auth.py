from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import UserSignUp, UserLogin, UserResponse, TokenResponse
from app.services.auth_service import AuthService
from app.security import create_access_token, get_current_user
from app.services.rate_limit_service import rate_limiter_dependency

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limiter_dependency(limit=20, window=60))]
)
def signup(data: UserSignUp, db: Session = Depends(get_db)):
    """Creates a new user account and returns a JWT access token."""
    user = AuthService.create_user(db=db, email=data.email, password=data.password)
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limiter_dependency(limit=30, window=60))]
)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """Authenticates credentials and returns a JWT access token."""
    user = AuthService.authenticate_user(db=db, email=data.email, password=data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user=Depends(get_current_user)):
    """Returns profile information for the authenticated user."""
    return UserResponse.model_validate(current_user)
