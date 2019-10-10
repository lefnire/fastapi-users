from datetime import datetime, timedelta

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from starlette import status
from starlette.responses import Response

from fastapi_users.authentication import BaseAuthentication
from fastapi_users.db import BaseUserDatabase
from fastapi_users.models import BaseUserDB

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def generate_jwt(data: dict, lifetime_seconds: int, secret: str, algorithm: str) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(seconds=lifetime_seconds)
    payload["exp"] = expire
    return jwt.encode(payload, secret, algorithm=algorithm).decode("utf-8")


class JWTAuthentication(BaseAuthentication):
    """
    Authentication using a JWT.

    :param secret: Secret used to encode the JWT.
    :param lifetime_seconds: Lifetime duration of the JWT in seconds.
    """

    algorithm: str = "HS256"
    secret: str
    lifetime_seconds: int

    def __init__(self, secret: str, lifetime_seconds: int):
        self.secret = secret
        self.lifetime_seconds = lifetime_seconds

    async def get_login_response(self, user: BaseUserDB, response: Response):
        data = {"user_id": user.id}
        token = generate_jwt(data, self.lifetime_seconds, self.secret, self.algorithm)

        return {"token": token}

    def get_authentication_method(self, user_db: BaseUserDatabase):
        async def authentication_method(token: str = Depends(oauth2_scheme)):
            credentials_exception = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED
            )

            try:
                data = jwt.decode(token, self.secret, algorithms=[self.algorithm])
                user_id = data.get("user_id")
                if user_id is None:
                    raise credentials_exception
            except jwt.PyJWTError:
                raise credentials_exception

            user = await user_db.get(user_id)
            if user is None or not user.is_active:
                raise credentials_exception

            return user

        return authentication_method