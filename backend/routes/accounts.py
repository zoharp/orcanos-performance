"""
Account management routes
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from backend.models import Account
from backend.services.database import get_db
from backend.services.encryption import get_encryption_service

router = APIRouter()


class AccountRequest(BaseModel):
    name: str
    url: str
    password: str
    enabled: bool = True


class AccountResponse(BaseModel):
    id: int
    name: str
    url: str
    enabled: bool
    model_config = {"from_attributes": True}


@router.get("/", response_model=List[AccountResponse])
async def list_accounts(db: Session = Depends(get_db)):
    return db.query(Account).all()


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Account not found")
    return account


@router.post("/", response_model=AccountResponse)
async def create_account(request: AccountRequest, db: Session = Depends(get_db)):
    if not request.name.strip():
        raise HTTPException(400, "Account name is required")
    if not request.url.strip():
        raise HTTPException(400, "Account URL is required")
    if not request.password:
        raise HTTPException(400, "Password is required")

    existing = db.query(Account).filter(Account.name == request.name).first()
    if existing:
        raise HTTPException(400, f"Account '{request.name}' already exists")

    try:
        enc = get_encryption_service()
        encrypted_password = enc.encrypt(request.password)
    except Exception as e:
        raise HTTPException(500, f"Encryption error: {e}")

    account = Account(
        name=request.name,
        url=request.url,
        encrypted_password=encrypted_password,
        enabled=request.enabled,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(account_id: int, request: AccountRequest, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Account not found")

    account.name = request.name
    account.url = request.url
    account.enabled = request.enabled

    if request.password:
        try:
            enc = get_encryption_service()
            account.encrypted_password = enc.encrypt(request.password)
        except Exception as e:
            raise HTTPException(500, f"Encryption error: {e}")

    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=204)
async def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Account not found")
    db.delete(account)
    db.commit()
