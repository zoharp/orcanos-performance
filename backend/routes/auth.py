"""
Authentication routes
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.services.database import get_db
from backend.services.auth import verify_password, create_access_token, verify_google_token
from backend.models import User

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class GoogleLoginRequest(BaseModel):
    credential: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(user.username, user.role)
    return LoginResponse(access_token=token, username=user.username, role=user.role)


@router.post("/google", response_model=LoginResponse)
def google_login(request: GoogleLoginRequest, db: Session = Depends(get_db)):
    google_claims = verify_google_token(request.credential)
    email = google_claims["email"]

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(username=email, email=email, role="admin")
        db.add(user)
        db.commit()

    token = create_access_token(user.username, user.role)
    return LoginResponse(access_token=token, username=user.username, role=user.role)


@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}
