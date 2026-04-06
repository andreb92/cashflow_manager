from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_user
from app.models.user import User
from app.services.auth import verify_password

router = APIRouter(prefix="/users", tags=["users"])

COOKIE_NAME = "access_token"
OIDC_ID_TOKEN_COOKIE = "oidc_id_token"


class DeleteMeRequest(BaseModel):
    password: Optional[str] = None


# /me MUST be registered before /{id} to avoid route shadowing
@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id, "email": current_user.email, "name": current_user.name,
        "has_password": bool(current_user.hashed_password),
        "has_oidc": bool(current_user.oidc_sub),
    }


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
