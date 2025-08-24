from functools import wraps
from typing import Optional, Callable, Any

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from fast_api_builder.utils.config import get_user_model
from fast_api_builder.auth.auth import Auth
from fast_api_builder.auth.jwt_handler import JWTHandler

User = get_user_model()


class JWTMiddleware(BaseHTTPMiddleware):
    def __init__(self,
                 app,
                 redis_cli,
                 secret_key,
                 reset_secret,
                 access_exp: int = 60, refresh_exp: int = 3600,
                 algorithm="HS256", ):
        super().__init__(app)
        self.secret_key = secret_key

        self.jwt_handler = JWTHandler(redis_cli=redis_cli, secret_key=secret_key,
                                      reset_secret=reset_secret,
                                      access_exp=access_exp,
                                      refresh_exp=refresh_exp,
                                      algorithm=algorithm,
                                      )

    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get('authorization')
        if auth_header:
            try:
                token = auth_header.split(" ")[1]
                # Decode token and attach to request state
                payload = self.jwt_handler.get_data(token)
                if payload.get('data') is None:
                    request.state.user = None
                    request.state.auth_error = payload.get('error')
                else:
                    request.state.user = payload.get('data')
                    request.state.auth_error = payload.get('error')

                    await Auth.init(
                        user_info=payload.get('data')
                    )

            except Exception as e:
                print(e)
                request.state.user = None
                request.state.auth_error = str(e)
        else:
            request.state.user = None
            request.state.auth_error = 'INVALID'
        # Proceed to the next middleware or GraphQL request
        response = await call_next(request)
        return response


def authorize(required_permissions: Optional[list] = None):
    def decorator(func: Callable):
        # For async functions
        @wraps(func)
        async def async_wrapper(request: Request, *args, **kwargs) -> Any:
            current_user = request.state.user

            if current_user is None:
                raise HTTPException(status_code=403, detail="User not authenticated")

            if required_permissions:
                user_obj = await User.filter(id=current_user.get('user_id')).prefetch_related(
                    'groups__permissions').get_or_none()
                if not user_obj:
                    raise HTTPException(status_code=403, detail="User not authenticated")

                # Now you can use `user_obj` which already has the prefetched data
                user: User = user_obj

                # Query the permission codes directly using .values_list() across the user's groups
                permission_codes = await user.groups.all().values_list('permissions__code', flat=True)

                # Return unique permission codes as a list
                user_permissions = list(set(permission_codes))
                has_permission = any(perm in user_permissions for perm in required_permissions)
                if has_permission or user.is_superuser:
                    return await func(request, *args, **kwargs)
                raise HTTPException(status_code=403, detail="User is not authorized to access")

            return await func(request, *args, **kwargs)

        return async_wrapper

    return decorator
