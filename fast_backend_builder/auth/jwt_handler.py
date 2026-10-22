import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict

import jwt


class JWTHandler:
    def __init__(
        self,
        redis_cli,
        secret_key,
        reset_secret,
        access_exp: int = 60,
        refresh_exp: int = 3600,
        algorithm: str = "HS256",
    ):
        self.redis = redis_cli
        self.secret_key = secret_key
        self.reset_secret = reset_secret
        self.algorithm = algorithm
        self.access_exp = access_exp
        self.refresh_exp = refresh_exp

    # --------------------------------------------------
    # JWT helpers
    # --------------------------------------------------

    def create_jwt_token(
        self,
        data: dict,
        expires_delta: timedelta,
    ) -> str:
        """Create a JWT with an expiration timestamp."""
        payload = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        payload["exp"] = expire

        return jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm,
        )

    def get_data(self, token: str) -> Dict:
        """Decode an access/refresh JWT and return its payload."""
        try:
            data = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            return {"data": data, "error": None}

        except jwt.exceptions.ExpiredSignatureError:
            return {"data": None, "error": "EXPIRED"}

        except jwt.exceptions.InvalidTokenError:
            return {"data": None, "error": "INVALID"}

    # --------------------------------------------------
    # Reset-password tokens
    # --------------------------------------------------

    async def create_reset_password_token(
        self,
        data: dict,
        expires_delta: timedelta,
    ) -> str:
        """Create a reset token and store it with a Redis TTL."""
        seconds = int(expires_delta.total_seconds())
        if seconds <= 0:
            raise ValueError("Reset token lifetime must be positive")

        payload = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        payload["exp"] = expire

        token = jwt.encode(
            payload,
            self.reset_secret,
            algorithm=self.algorithm,
        )

        await self.redis.set(
            f"reset_token:{token}",
            "valid",
            ex=seconds,
        )

        return token

    async def get_reset_password_data(
        self,
        token: str,
    ) -> Dict | None:
        """Validate a reset token against Redis and decode its JWT."""
        try:
            payload = jwt.decode(
                token,
                self.reset_secret,
                algorithms=[self.algorithm],
            )
        except jwt.exceptions.InvalidTokenError:
            return None

        exists = await self.redis.exists(f"reset_token:{token}")
        if not exists:
            return None

        return payload

    async def invalidate_reset_token(self, token: str) -> None:
        """Invalidate a reset token."""
        await self.redis.delete(f"reset_token:{token}")

    # --------------------------------------------------
    # Access tokens
    # --------------------------------------------------

    def create_access_token(self, data: Dict) -> str:
        """Create an access token."""
        return self.create_jwt_token(
            data,
            timedelta(minutes=self.access_exp),
        )

    # --------------------------------------------------
    # Refresh tokens: individual Redis keys with TTL
    # --------------------------------------------------

    @staticmethod
    def _refresh_token_key(token: str) -> str:
        """Return a Redis key based on the SHA-256 token hash."""
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return f"refresh_token:{digest}"

    async def create_refresh_token(self, data: Dict) -> str:
        """
        Create a refresh JWT and store its hash in Redis.
        Redis automatically expires the key after the token lifetime.
        """
        expires_delta = timedelta(minutes=self.refresh_exp)
        seconds = int(expires_delta.total_seconds())

        if seconds <= 0:
            raise ValueError("Refresh token lifetime must be positive")

        token = self.create_jwt_token(data, expires_delta)
        key = self._refresh_token_key(token)

        await self.redis.set(key, "1", ex=seconds)

        return token

    async def check_refresh_token(
        self,
        refresh_token: str,
    ) -> Dict | None:
        """
        Check that the token exists in Redis and is a valid JWT.
        Returns the decoded payload or None.
        """
        key = self._refresh_token_key(refresh_token)

        # Do not retrieve a global collection of refresh tokens.
        exists = await self.redis.exists(key)
        if not exists:
            return None

        token_data = self.get_data(refresh_token)

        if token_data["error"] is not None:
            await self.redis.delete(key)
            return None

        return token_data["data"]

    async def invalidate_refresh_token(
        self,
        refresh_token: str,
    ) -> None:
        """Revoke a refresh token by deleting its Redis key."""
        await self.redis.delete(
            self._refresh_token_key(refresh_token)
        )

    # --------------------------------------------------
    # Token generation
    # --------------------------------------------------

    async def generate_tokens(self, data: Dict) -> Dict:
        """Generate an access token and a refresh token."""
        access_token = self.create_access_token(data)
        refresh_token = await self.create_refresh_token(data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }