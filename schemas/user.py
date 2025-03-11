# app/schemas/user.py
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
import uuid


# Token schema for authentication
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: Optional[str] = None


# Base User schema with common attributes
class UserBase(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True


# Schema for user creation
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    @classmethod
    @field_validator('email')
    def validate_email(cls, v):
        if not v:
            raise ValueError('Email cannot be empty')

        # Email is already validated by EmailStr, but we can add custom rules
        if len(v) > 100:
            raise ValueError('Email must be less than 100 characters')

        # Check for common domains if needed
        allowed_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'ashesi.edu.gh']
        domain = v.split('@')[-1].lower()
        if domain not in allowed_domains:
            raise ValueError(f'Email domain not supported. Please use one of: {", ".join(allowed_domains)}')

        return v

    @classmethod
    @field_validator('password')
    def password_validation(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')

        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')

        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')

        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one number')

        special_chars = "!@#$%^&*()-_=+[]{}|;:,.<>?/~`"
        if not any(char in special_chars for char in v):
            raise ValueError(f'Password must contain at least one special character ({special_chars})')

        # Check for common passwords (you might want to expand this list)
        common_passwords = ['password', 'password123', '12345678', 'qwerty123']
        if v.lower() in common_passwords:
            raise ValueError('This password is too common. Please choose a stronger password')

        return v


# Schema for user update
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None

    class Config:
        extra = "forbid"  # Prevents additional fields


# Schema for changing password
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator('new_password')
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError('New password must be at least 8 characters')
        return v


# Base response schema for User
class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Extended response schema for User profile
class UserProfileResponse(UserResponse):
    contribution_count: int
    accepted_contributions: int
    reputation_score: float
    total_hours_speech: int
    total_sentences_translated: int
    total_tokens_produced: int
    total_points: int
    acceptance_rate: Optional[float] = None


# Schema for top contributors response
class TopContributorResponse(BaseModel):
    id: str
    username: str
    reputation_score: float
    contribution_count: int
    accepted_contributions: int
    total_points: int

    class Config:
        orm_mode = True
