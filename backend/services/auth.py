from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import jwt
from sqlalchemy.engine import Engine

from config.settings import settings
from core.exceptions import UnauthorizedError
from core.models import User
from db.repositories.users import UsersRepository


class AuthService:
    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine
        self.users = UsersRepository()

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

    def authenticate(self, username: str, password: str) -> User | None:
        if not username or not password:
            return None
        with self._require_engine().begin() as conn:
            row = self.users.get_by_username(conn, username)
        if not row or not self.verify_password(password, row["password_hash"]):
            return None
        return User.model_validate(row)

    def get_user(self, user_id: UUID) -> User | None:
        with self._require_engine().begin() as conn:
            row = self.users.get_by_id(conn, user_id)
        if not row:
            return None
        return User.model_validate(row)

    def _require_engine(self) -> Engine:
        if self._engine is None:
            raise RuntimeError("AuthService requires a database engine")
        return self._engine
