"""
SQLite-based Authentication Middleware

Simple authentication using SQLite database for local development.
Replace with HPE SSO in production.

Task Reference: Phase 3, Task 3.1
"""

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import sqlite3
import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional
import logging


security = HTTPBearer()


class AuthService:
    """SQLite-based authentication service"""

    def __init__(self, db_path: str = "data/users.db"):
        """
        Initialize Auth Service

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.secret_key = "your-secret-key-change-in-production"  # TODO: Move to env
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60

        # Initialize database
        self._init_db()

    def _init_db(self):
        """Initialize users database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create sessions table for token management
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        conn.commit()
        conn.close()

        self.logger.info(f"Auth database initialized at {self.db_path}")

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None
    ) -> dict:
        """
        Create new user

        Args:
            username: Unique username
            email: User email
            password: Plain text password (will be hashed)
            full_name: Optional full name

        Returns:
            User dictionary
        """
        password_hash = self._hash_password(password)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO users (username, email, password_hash, full_name)
                VALUES (?, ?, ?, ?)
            """, (username, email, password_hash, full_name))

            user_id = cursor.lastrowid
            conn.commit()
            conn.close()

            self.logger.info(f"User created: {username}")

            return {
                "id": user_id,
                "username": username,
                "email": email,
                "full_name": full_name
            }

        except sqlite3.IntegrityError as e:
            self.logger.error(f"User creation failed: {e}")
            raise ValueError("Username or email already exists")

    def authenticate(self, username: str, password: str) -> Optional[dict]:
        """
        Authenticate user

        Args:
            username: Username
            password: Password

        Returns:
            User dict if authenticated, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, username, email, password_hash, full_name, is_active
            FROM users
            WHERE username = ?
        """, (username,))

        user = cursor.fetchone()
        conn.close()

        if not user:
            return None

        if not user['is_active']:
            return None

        # Verify password
        if self._verify_password(password, user['password_hash']):
            return {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "full_name": user['full_name']
            }

        return None

    def create_access_token(self, user: dict) -> str:
        """
        Create JWT access token

        Args:
            user: User dictionary

        Returns:
            JWT token string
        """
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        token_data = {
            "sub": user['username'],
            "user_id": user['id'],
            "email": user['email'],
            "exp": expire
        }

        token = jwt.encode(token_data, self.secret_key, algorithm=self.algorithm)

        # Store session
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO sessions (user_id, token, expires_at)
            VALUES (?, ?, ?)
        """, (user['id'], token, expire))

        conn.commit()
        conn.close()

        return token

    def verify_token(self, token: str) -> Optional[dict]:
        """
        Verify JWT token

        Args:
            token: JWT token string

        Returns:
            User data if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check if token exists in sessions and not expired
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT user_id FROM sessions
                WHERE token = ? AND expires_at > datetime('now')
            """, (token,))

            session = cursor.fetchone()
            conn.close()

            if not session:
                return None

            return payload

        except jwt.ExpiredSignatureError:
            self.logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            self.logger.warning("Invalid token")
            return None

    def _hash_password(self, password: str) -> str:
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return self._hash_password(password) == password_hash


# Global auth service instance
auth_service = AuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Dependency to get current authenticated user

    Usage in routes:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"message": f"Hello {user['username']}"}
    """
    token = credentials.credentials

    user = auth_service.verify_token(token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Optional authentication - returns None if not authenticated
    """
    if not credentials:
        return None

    return auth_service.verify_token(credentials.credentials)


def main():
    """Create test users for development"""
    auth = AuthService()

    # Create test users
    test_users = [
        {
            "username": "admin",
            "email": "admin@kms.local",
            "password": "admin123",
            "full_name": "Admin User"
        },
        {
            "username": "test_user",
            "email": "test@kms.local",
            "password": "test123",
            "full_name": "Test User"
        },
        {
            "username": "grs_agent",
            "email": "grs@hpe.com",
            "password": "grs123",
            "full_name": "GRS Support Agent"
        }
    ]

    for user_data in test_users:
        try:
            user = auth.create_user(**user_data)
            print(f"✓ Created user: {user['username']}")
        except ValueError as e:
            print(f"✗ User {user_data['username']} already exists")

    # Test authentication
    user = auth.authenticate("admin", "admin123")
    if user:
        token = auth.create_access_token(user)
        print(f"\n✓ Test token for admin: {token[:50]}...")

        # Verify token
        verified = auth.verify_token(token)
        print(f"✓ Token verified: {verified['username']}")


if __name__ == "__main__":
    main()
