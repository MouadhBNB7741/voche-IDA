from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# --- Request Schemas ---

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str
    last_name: str
    user_type: str = Field(..., pattern="^(patient|hcp|org_member|admin)$")

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class PasswordUpdateRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

# --- Response Schemas ---

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_type: str