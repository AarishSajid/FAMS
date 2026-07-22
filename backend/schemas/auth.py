"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel
from datetime import datetime


class LoginRequest(BaseModel):
    email: str | None = None
    username: str | None = None
    password: str


class RefreshRequest(BaseModel):
    refreshToken: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str | None = None
    firstName: str | None = None
    lastName: str | None = None
    role: str
    isActive: bool
    serviceCenterId: int | None = None
    availabilityStatus: str | None = None
    lastLogin: datetime | None = None

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    message: str
    user: UserResponse
    accessToken: str
    refreshToken: str


class MeResponse(BaseModel):
    id: str
    email: str
    username: str | None = None
    role: str
    firstName: str | None = None
    lastName: str | None = None
    serviceCenterId: int | None = None

    model_config = {"from_attributes": True}
