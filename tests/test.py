import jwt  # This works after installing PyJWT
# or
from jwt import encode, decode  # If you want to be more specific
from datetime import datetime, timedelta
from typing import Optional

SECRET_KEY = "your-secret-key"  # Replace with your actual secret key
ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def get_password_hash(password: str):
    # Implement password hashing (e.g., using bcrypt or passlib)
    # This is a placeholder - replace with actual hashing
    return password  # Do NOT use in production!

def verify_password(plain_password: str, hashed_password: str):
    # Implement password verification
    # This is a placeholder - replace with actual verification
    return plain_password == hashed_password
