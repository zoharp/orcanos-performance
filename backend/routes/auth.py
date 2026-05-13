"""
Authentication routes
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.services.database import get_db
from backend.services.auth import verify_password, create_access_token
from backend.models import User

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


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


@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}
