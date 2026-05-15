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
from backend.services.auth import get_current_user, require_admin
from backend.services.manual_tester import get_manual_tester_session

router = APIRouter(dependencies=[Depends(get_current_user)])


class AccountRequest(BaseModel):
    name: str
    url: str
    password: str
    enabled: bool = True
    version: str = ""


class AccountResponse(BaseModel):
    id: int
    name: str
    url: str
    enabled: bool
    version: str = ""
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
        version=request.version,
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
    account.version = request.version

    if request.password:
        try:
            enc = get_encryption_service()
            account.encrypted_password = enc.encrypt(request.password)
        except Exception as e:
            raise HTTPException(500, f"Encryption error: {e}")

    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Account not found")
    db.delete(account)
    db.commit()


@router.post("/{account_id}/manual-test/start")
async def start_manual_test(account_id: int, db: Session = Depends(get_db)):
    """Start a manual test session for an account (opens Chrome browser with auto-login)"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Account not found")

    enc = get_encryption_service()
    password = enc.decrypt(account.encrypted_password)

    tester = get_manual_tester_session()
    try:
        tester.start(account_id, account.url, "orcanos.tech", password)
        return {"status": "started", "account_id": account_id}
    except RuntimeError as e:
        raise HTTPException(400, str(e))


@router.post("/{account_id}/manual-test/stop")
async def stop_manual_test(account_id: int):
    """Stop a manual test session for an account"""
    tester = get_manual_tester_session()
    tester.stop(account_id)
    return {"status": "stopped", "account_id": account_id}


@router.get("/{account_id}/manual-test/status")
async def get_manual_test_status(account_id: int):
    """Get the status of a manual test session"""
    tester = get_manual_tester_session()
    return tester.get_status(account_id)
