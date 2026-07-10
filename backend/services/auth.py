from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import jwt

from config.settings import settings
from core.exceptions import UnauthorizedError


class AuthService:
    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

    def verify_password(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode(), password_hash.encode())

    def create_token(self, user_id: UUID) -> str:
        exp = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
        payload = {"sub": str(user_id), "exp": exp}
        return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

    def decode_token(self, token: str) -> UUID:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
            return UUID(payload["sub"])
        except (jwt.PyJWTError, ValueError, KeyError) as exc:
            raise UnauthorizedError("Invalid session") from exc

    def decode_token_optional(self, token: str) -> UUID | None:
        try:
            return self.decode_token(token)
        except UnauthorizedError:
            return None
