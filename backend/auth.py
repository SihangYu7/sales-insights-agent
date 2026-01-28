"""
AI Agent Backend - Authentication Service
==========================================
JWT-based authentication with bcrypt password hashing.

KEY CONCEPTS:
- JWT: JSON Web Tokens for stateless authentication
- bcrypt: Secure password hashing algorithm
- Access tokens: Short-lived tokens for API access
- Refresh tokens: Long-lived tokens to get new access tokens
"""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify, g

from database import SessionLocal, User

# Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
JWT_ALGORITHM = "HS256"


# =============================================================================
# PASSWORD HASHING
# =============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    bcrypt automatically handles:
    - Salt generation (random data added to password)
    - Multiple rounds of hashing (makes brute-force attacks slow)
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.
    Returns True if password matches, False otherwise.
    """
    password_bytes = password.encode('utf-8')
    hash_bytes = password_hash.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hash_bytes)


# =============================================================================
# JWT TOKEN FUNCTIONS
# =============================================================================

def create_access_token(user_id: int, email: str) -> str:
    """
    Create a JWT access token.

    Payload contains:
    - sub: Subject (user_id)
    - email: User's email
    - exp: Expiration timestamp
    - iat: Issued at timestamp
    - type: Token type (access)
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": now + JWT_ACCESS_TOKEN_EXPIRES,
        "iat": now,
        "type": "access"
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """
    Create a JWT refresh token.
    Used to get new access tokens without re-authenticating.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "exp": now + JWT_REFRESH_TOKEN_EXPIRES,
        "iat": now,
        "type": "refresh"
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Returns the payload if valid.
    Raises jwt.InvalidTokenError if invalid or expired.
    """
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])


def get_token_from_header() -> str | None:
    """
    Extract JWT token from Authorization header.

    Expected format: "Bearer <token>"
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix
    return None


# =============================================================================
# USER FUNCTIONS
# =============================================================================

def create_user(email: str, password: str, name: str = None) -> dict:
    """
    Create a new user in the database.

    Returns:
        dict with success status and user data or error message
    """
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            return {"success": False, "error": "Email already registered"}

        # Create new user
        user = User(
            email=email,
            password_hash=hash_password(password),
            name=name
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "user": user.to_dict()
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def authenticate_user(email: str, password: str) -> dict:
    """
    Authenticate a user with email and password.

    Returns:
        dict with success status, tokens, and user data
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()

        if not user:
            return {"success": False, "error": "Invalid email or password"}

        if not user.is_active:
            return {"success": False, "error": "Account is deactivated"}

        if not verify_password(password, user.password_hash):
            return {"success": False, "error": "Invalid email or password"}

        # Generate tokens
        access_token = create_access_token(user.id, user.email)
        refresh_token = create_refresh_token(user.id)

        return {
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user.to_dict()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def get_user_by_id(user_id: int) -> User | None:
    """Get a user by their ID."""
    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == user_id).first()
    finally:
        db.close()


def refresh_access_token(refresh_token: str) -> dict:
    """
    Use a refresh token to get a new access token.

    Returns:
        dict with success status and new access token
    """
    try:
        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            return {"success": False, "error": "Invalid token type"}

        user_id = payload.get("sub")
        user = get_user_by_id(user_id)

        if not user:
            return {"success": False, "error": "User not found"}

        if not user.is_active:
            return {"success": False, "error": "Account is deactivated"}

        new_access_token = create_access_token(user.id, user.email)

        return {
            "success": True,
            "access_token": new_access_token
        }
    except jwt.ExpiredSignatureError:
        return {"success": False, "error": "Refresh token expired"}
    except jwt.InvalidTokenError:
        return {"success": False, "error": "Invalid refresh token"}


# =============================================================================
# AUTH MIDDLEWARE (Decorator)
# =============================================================================

def require_auth(f):
    """
    Decorator to protect routes that require authentication.

    Usage:
        @app.route('/api/protected')
        @require_auth
        def protected_route():
            user_id = g.user_id  # Access user info
            return jsonify({"message": "Hello!"})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_header()

        if not token:
            return jsonify({"error": "Missing authentication token"}), 401

        try:
            payload = decode_token(token)

            if payload.get("type") != "access":
                return jsonify({"error": "Invalid token type"}), 401

            # Store user info in Flask's g object for use in route
            g.user_id = payload.get("sub")
            g.user_email = payload.get("email")

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)

    return decorated_function


# =============================================================================
# OPTIONAL AUTH MIDDLEWARE
# =============================================================================

def optional_auth(f):
    """
    Decorator for routes where auth is optional.
    Sets g.user_id if token is valid, otherwise sets it to None.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_header()

        g.user_id = None
        g.user_email = None

        if token:
            try:
                payload = decode_token(token)
                if payload.get("type") == "access":
                    g.user_id = payload.get("sub")
                    g.user_email = payload.get("email")
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                pass  # Token invalid, but route is still accessible

        return f(*args, **kwargs)

    return decorated_function
