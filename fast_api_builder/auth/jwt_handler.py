from datetime import timedelta, datetime
from typing import Dict

import jwt


class JWTHandler:
    def __init__(self, redis_cli, secret_key, reset_secret, access_exp: int = 60, refresh_exp: int = 3600, algorithm="HS256", ):
        super().__init__()
        self.redis = redis_cli
        self.secret_key = secret_key
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_exp = access_exp
        self.refresh_exp = refresh_exp
        self.reset_secret = reset_secret

    def create_jwt_token(self, data: dict, expires_delta: timedelta) -> str:
        """Creates an JWT Token with `data` and `expire_delta`"""
        data = data.copy()
        expire = datetime.now() + expires_delta
        data.update({"exp": expire})
        encoded_jwt = jwt.encode(data, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def get_data(self, token: str) -> Dict:
        """Fastapi Dependency to get JWT Data from the User"""
        try:
            data = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.exceptions.InvalidTokenError as e:
            if isinstance(e, jwt.exceptions.ExpiredSignatureError):
                return {
                    'data': None,
                    'error': "EXPIRED"
                }
            else:
                return {
                    'data': None,
                    'error': 'INVALID'
                }
        return {
            'data': data,
            'error': None
        }

    def create_reset_password_token(self, data: dict, expires_delta: timedelta) -> str:
        """Creates an JWT Token with `data` and `expire_delta`"""
        data = data.copy()
        expire = datetime.now() + expires_delta
        data.update({"exp": expire})
        encoded_jwt = jwt.encode(data, self.reset_secret, algorithm=self.algorithm)
        return encoded_jwt

    def get_reset_password_data(self, token: str) -> Dict | None:
        """Fastapi Dependency to get JWT Data from the User"""
        try:
            data = jwt.decode(token, self.reset_secret, algorithms=[self.algorithm])
        except jwt.exceptions.InvalidTokenError as e:
            if isinstance(e, jwt.exceptions.ExpiredSignatureError):
                print('Token is expired')
                return None
            else:
                print("Token is invalid")
                return None
        return data

    def create_access_token(self, data: Dict) -> str:
        """Creates an JWT Access Token with `data` and expires after `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`"""
        return self.create_jwt_token(data, timedelta(minutes=self.access_exp))

    def create_refresh_token(self, data: Dict) -> str:
        """Creates an Refresh Token with the `user_uid` and needs `redis`"""
        refresh_token: str = self.create_jwt_token(data, timedelta(minutes=self.refresh_exp))
        self.redis.sadd("refresh_tokens", refresh_token)
        self.redis.close()
        return refresh_token

    def invalidate_refresh_token(self, refresh_token: str) -> None:
        """Invalidates a Refresh Token"""
        if refresh_token in self.redis.smembers("refresh_tokens"):
            self.redis.srem("refresh_tokens", refresh_token)
        self.redis.close()

    def check_refresh_token(self, refresh_token: str) -> Dict | None:
        """Checks if a Refresh Token is valid (in Redis Cache)"""
        if refresh_token in self.redis.smembers("refresh_tokens"):
            token_data = self.get_data(refresh_token)
            return token_data.get('data')
        self.redis.close()
        return None

    def generate_tokens(self, data: Dict) -> Dict:
        """Generates Access and Refresh Token with `data`, `user_uid` and needs self.redis"""
        access_token: str = self.create_access_token(data)
        refresh_token: str = self.create_refresh_token(data)
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
