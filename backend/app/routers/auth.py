from typing import Annotated
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_user
from app.models.user import User, gen_uuid
from app.schemas.auth import RegisterRequest, LoginRequest, UserOut
from app.services.auth import hash_password, verify_password, create_access_token
from app.config import get_settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

COOKIE_NAME = "access_token"


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * get_settings().jwt_expire_days,
        secure=not get_settings().development_mode,
    )


@router.post("/register", response_model=UserOut)
def register(body: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.basic_auth_enabled:
        raise HTTPException(status_code=403, detail="Basic auth disabled")
    if db.query(User).filter_by(email=body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        id=gen_uuid(),
        email=body.email,
        hashed_password=hash_password(body.password),
        name=body.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.id})
    _set_auth_cookie(response, token)
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        has_password=True,
        has_oidc=bool(user.oidc_sub),
    )


@router.post("/login", response_model=UserOut)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=body.email).first()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.id})
    _set_auth_cookie(response, token)
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        has_password=True,
        has_oidc=bool(user.oidc_sub),
    )


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        has_password=bool(current_user.hashed_password),
        has_oidc=bool(current_user.oidc_sub),
    )


import secrets as _secrets
from app.services import oidc as _oidc

OIDC_STATE_COOKIE = "oidc_state"
OIDC_ID_TOKEN_COOKIE = "oidc_id_token"


@router.get("/oidc/login")
async def oidc_login(response: Response):
    settings = get_settings()
    if not settings.oidc_enabled:
        raise HTTPException(status_code=404, detail="OIDC not enabled")
    endpoints = await _oidc.discover_endpoints(settings.oidc_issuer_url)
    state = _secrets.token_urlsafe(16)
    auth_url = (
        f"{endpoints['authorization_endpoint']}"
        f"?response_type=code&client_id={settings.oidc_client_id}"
        f"&redirect_uri={settings.oidc_redirect_uri}"
        f"&scope=openid+email+profile&state={state}"
    )
    response.set_cookie(key=OIDC_STATE_COOKIE, value=state, httponly=True, samesite="lax", max_age=600, secure=not settings.development_mode)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=auth_url)


@router.get("/oidc/callback")
async def oidc_callback(
    code: str,
    state: str,
    response: Response,
    db: Session = Depends(get_db),
    oidc_state: Annotated[str | None, Cookie()] = None,
):
    settings = get_settings()
    if not settings.oidc_enabled:
        raise HTTPException(status_code=404, detail="OIDC not enabled")
    if oidc_state is None or oidc_state != state:
        raise HTTPException(status_code=400, detail="Invalid state")
    endpoints = await _oidc.discover_endpoints(settings.oidc_issuer_url)
    tokens = await _oidc.exchange_code(
        code,
        endpoints["token_endpoint"],
        settings.oidc_redirect_uri,
        settings.oidc_client_id,
        settings.oidc_client_secret,
    )
    userinfo_ep = endpoints.get("userinfo_endpoint")
    if userinfo_ep:
        info = await _oidc.get_userinfo(userinfo_ep, tokens["access_token"])
    else:
        import jwt as _pyjwt
        from jwt import PyJWKClient
        id_token = tokens.get("id_token", "")
        jwks_client = PyJWKClient(endpoints["jwks_uri"])
        signing_key = jwks_client.get_signing_key_from_jwt(id_token)
        info = _pyjwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.oidc_client_id,
        )

    sub = info.get("sub") or info.get("oid")
    email = info.get("email")
    name = info.get("name", "")

    user = db.query(User).filter_by(oidc_sub=sub).first()
    if not user and email:
        user = db.query(User).filter_by(email=email).first()
    if not user:
        user = User(id=gen_uuid(), email=email, oidc_sub=sub, name=name)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not user.oidc_sub:
        user.oidc_sub = sub
        db.commit()

    token = create_access_token({"sub": user.id})
    _set_auth_cookie(response, token)
    if tokens.get("id_token"):
        enc = _oidc.encrypt_cookie(tokens["id_token"], settings.session_encryption_key)
        response.set_cookie(key=OIDC_ID_TOKEN_COOKIE, value=enc, httponly=True, samesite="lax", secure=not settings.development_mode)
    response.delete_cookie(key=OIDC_STATE_COOKIE)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/")


@router.get("/oidc/logout")
async def oidc_logout(
    response: Response,
    oidc_id_token: Annotated[str | None, Cookie()] = None,
):
    settings = get_settings()
    response.delete_cookie(key=COOKIE_NAME)
    response.delete_cookie(key=OIDC_ID_TOKEN_COOKIE)
    if settings.oidc_enabled and oidc_id_token:
        try:
            endpoints = await _oidc.discover_endpoints(settings.oidc_issuer_url)
            end_session = endpoints.get("end_session_endpoint")
            if end_session:
                id_token = _oidc.decrypt_cookie(oidc_id_token, settings.session_encryption_key)
                logout_url = f"{end_session}?id_token_hint={id_token}&post_logout_redirect_uri=/"
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url=logout_url)
        except Exception:
            pass
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/login")
