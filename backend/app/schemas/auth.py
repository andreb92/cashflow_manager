from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Annotated, Optional


class RegisterRequest(BaseModel):
    email: str
    password: Annotated[str, Field(min_length=8)]
    name: str = ""

    @field_validator("email")
    @classmethod
    def email_must_contain_at(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email address: must contain '@'")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthConfigOut(BaseModel):
    oidc_enabled: bool
    basic_auth_enabled: bool


class UserOut(BaseModel):
    id: str
    email: Optional[str]
    name: str
    has_password: bool
    has_oidc: bool

    model_config = ConfigDict(from_attributes=True)
