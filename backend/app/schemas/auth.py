from pydantic import BaseModel, ConfigDict
from typing import Optional


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: Optional[str]
    name: str
    has_password: bool
    has_oidc: bool

    model_config = ConfigDict(from_attributes=True)
