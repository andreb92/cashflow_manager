from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_user
from app.models.user import User
from app.services.auth import verify_password, hash_password

router = APIRouter(prefix="/users", tags=["users"])

COOKIE_NAME = "access_token"
OIDC_ID_TOKEN_COOKIE = "oidc_id_token"


class DeleteMeRequest(BaseModel):
    password: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.put("/me/password")
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.hashed_password:
        raise HTTPException(status_code=400, detail="Account uses OIDC; no password to change")
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=422, detail="New password must be at least 8 characters")
    current_user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"ok": True}


@router.delete("/me")
def delete_me(
    body: DeleteMeRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Password-based users must supply a correct password; OIDC-only users are exempt.
    if current_user.hashed_password:
        if not body.password or not verify_password(body.password, current_user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid password")
    db.delete(current_user)
    db.commit()
    response.delete_cookie(COOKIE_NAME)
    response.delete_cookie(OIDC_ID_TOKEN_COOKIE)
    return {"ok": True}
