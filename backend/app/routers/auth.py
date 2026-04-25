from typing import Annotated
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_user
from app.models.user import User, gen_uuid
from app.schemas.auth import AuthConfigOut, LoginRequest, RegisterRequest, UserOut
from app.services.auth import hash_password, verify_password, create_access_token
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "access_token"


def _set_auth_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * settings.jwt_expire_days,
        secure=settings.cookie_secure if settings.cookie_secure is not None else not settings.development_mode,
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME)


def _clear_oidc_flow_cookies(response: Response) -> None:
    response.delete_cookie(key=OIDC_STATE_COOKIE)
    response.delete_cookie(key=OIDC_NONCE_COOKIE)


def _clear_oidc_session_cookie(response: Response) -> None:
    response.delete_cookie(key=OIDC_ID_TOKEN_COOKIE)


def _clear_all_auth_cookies(response: Response) -> None:
    _clear_auth_cookie(response)
    _clear_oidc_session_cookie(response)
    _clear_oidc_flow_cookies(response)


def _build_post_logout_redirect_uri(oidc_redirect_uri: str) -> str | None:
    parsed = urlsplit(oidc_redirect_uri)
    if not parsed.scheme or not parsed.netloc:
        return None

    callback_suffix = "/api/v1/auth/oidc/callback"
    if parsed.path.endswith(callback_suffix):
        login_base = parsed.path[: -len(callback_suffix)]
        login_path = f"{login_base}/login" if login_base else "/login"
    else:
        login_path = "/login"

    return urlunsplit((parsed.scheme, parsed.netloc, login_path, "", ""))


async def _build_oidc_logout_redirect(oidc_id_token: str | None) -> RedirectResponse | None:
    settings = get_settings()
    if not settings.oidc_enabled or not oidc_id_token:
        return None
    try:
        endpoints = await _oidc.discover_endpoints(settings.oidc_issuer_url)
        end_session = endpoints.get("end_session_endpoint")
        if not end_session:
            return None
        id_token = _oidc.decrypt_cookie(oidc_id_token, settings.session_encryption_key)
        if id_token is None:
            return None

        post_logout_redirect_uri = _build_post_logout_redirect_uri(settings.oidc_redirect_uri)
        if post_logout_redirect_uri is None:
            return None

        parsed_end_session = urlsplit(end_session)
        preserved_params = [
            (key, value)
            for key, value in parse_qsl(parsed_end_session.query, keep_blank_values=True)
            if key not in {"id_token_hint", "post_logout_redirect_uri"}
        ]
        preserved_params.extend(
            [
                ("id_token_hint", id_token),
                ("post_logout_redirect_uri", post_logout_redirect_uri),
            ]
        )
        logout_url = urlunsplit(
            parsed_end_session._replace(
                query=urlencode(preserved_params, doseq=True, quote_via=quote)
            )
        )
        redirect = RedirectResponse(url=logout_url)
        _clear_all_auth_cookies(redirect)
        return redirect
    except Exception:
        return None


@router.get("/config", response_model=AuthConfigOut)
def auth_config():
    settings = get_settings()
    return AuthConfigOut(
        oidc_enabled=settings.oidc_enabled,
        basic_auth_enabled=settings.basic_auth_enabled,
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
    settings = get_settings()
    if not settings.basic_auth_enabled:
        raise HTTPException(status_code=403, detail="Basic auth disabled")
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
async def logout(
    response: Response,
    oidc_id_token: Annotated[str | None, Cookie()] = None,
):
    redirect = await _build_oidc_logout_redirect(oidc_id_token)
    if redirect:
        return redirect
    _clear_all_auth_cookies(response)
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
import jwt as _pyjwt
from app.services import oidc as _oidc

OIDC_STATE_COOKIE = "oidc_state"
OIDC_NONCE_COOKIE = "oidc_nonce"
OIDC_ID_TOKEN_COOKIE = "oidc_id_token"


@router.get("/oidc/login")
async def oidc_login(response: Response):
    settings = get_settings()
    if not settings.oidc_enabled:
        raise HTTPException(status_code=404, detail="OIDC not enabled")
    endpoints = await _oidc.discover_endpoints(settings.oidc_issuer_url)
    state = _secrets.token_urlsafe(16)
    nonce = _secrets.token_urlsafe(16)
    auth_url = (
        f"{endpoints['authorization_endpoint']}"
        f"?response_type=code&client_id={settings.oidc_client_id}"
        f"&redirect_uri={settings.oidc_redirect_uri}"
        f"&scope=openid+email+profile&state={state}&nonce={nonce}"
    )
    redirect = RedirectResponse(url=auth_url)
    redirect.set_cookie(key=OIDC_STATE_COOKIE, value=state, httponly=True, samesite="lax", max_age=600, secure=not settings.development_mode)
    redirect.set_cookie(key=OIDC_NONCE_COOKIE, value=nonce, httponly=True, samesite="lax", max_age=600, secure=not settings.development_mode)
    return redirect


@router.get("/oidc/callback")
async def oidc_callback(
    code: str,
    state: str,
    response: Response,
    db: Session = Depends(get_db),
    oidc_state: Annotated[str | None, Cookie()] = None,
    oidc_nonce: Annotated[str | None, Cookie()] = None,
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
        # Verify nonce from ID token if present (without signature verification —
        # the userinfo call already authenticated the session via the access token)
        id_token = tokens.get("id_token")
        if id_token and oidc_nonce is not None:
            try:
                id_token_claims = _pyjwt.decode(id_token, options={"verify_signature": False})
            except Exception:
                id_token_claims = {}
            if id_token_claims.get("nonce") != oidc_nonce:
                raise HTTPException(status_code=400, detail="Invalid nonce")
    else:
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
        # Verify nonce for the no-userinfo path
        if oidc_nonce is not None and info.get("nonce") != oidc_nonce:
            raise HTTPException(status_code=400, detail="Invalid nonce")

    sub = info.get("sub") or info.get("oid")
    if not sub:
        raise HTTPException(status_code=400, detail="OIDC provider did not return a subject identifier")

    # B. Require email_verified before trusting the email claim
    email = info.get("email")
    email_verified = info.get("email_verified")
    if email and not email_verified:
        email = None  # ignore unverified email; create OIDC-only account without it

    name = info.get("name", "")

    # A. Lookup ONLY by oidc_sub — never auto-attach sub to a password-auth account
    user = db.query(User).filter_by(oidc_sub=sub).first()
    if not user:
        # Defensive: if another account already owns this email, don't collide on UNIQUE constraint
        if email and db.query(User).filter_by(email=email).first():
            email = None
        user = User(id=gen_uuid(), email=email, oidc_sub=sub, name=name)
        db.add(user)
        db.commit()
        db.refresh(user)

    redirect = RedirectResponse(url="/")
    token = create_access_token({"sub": user.id})
    _set_auth_cookie(redirect, token)
    if tokens.get("id_token"):
        enc = _oidc.encrypt_cookie(tokens["id_token"], settings.session_encryption_key)
        redirect.set_cookie(key=OIDC_ID_TOKEN_COOKIE, value=enc, httponly=True, samesite="lax", secure=not settings.development_mode)
    _clear_oidc_flow_cookies(redirect)
    return redirect


@router.get("/oidc/logout")
async def oidc_logout(
    response: Response,
    oidc_id_token: Annotated[str | None, Cookie()] = None,
    _current_user: User = Depends(get_current_user),
):
    redirect = await _build_oidc_logout_redirect(oidc_id_token)
    if redirect:
        return redirect
    redirect = RedirectResponse(url="/login")
    _clear_all_auth_cookies(redirect)
    return redirect
