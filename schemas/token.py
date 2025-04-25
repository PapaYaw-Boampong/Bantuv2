from pydantic import BaseModel


class Token(BaseModel):
    """
    Schema for authentication tokens
    """
    access_token: str
    refresh_token: str  # Add refresh token
    token_type: str = "bearer"  # Default to "bearer"
    expires_in: int  # Expiration time in minutes


# Define a schema for the refresh token request
class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str  # New refresh token (if rotated, otherwise the same)
    token_type: str = "bearer"  # Specifies token type
    expires_in: int  # Expiration time in seconds


class LogoutResponse(BaseModel):
    """
    Schema for logout response
    """
    success: bool
    message: str = "Logged out successfully"


class LogoutRequest(BaseModel):
    """
    Schema for logout request
    """
    refresh_token: str


