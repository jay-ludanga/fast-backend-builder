import contextlib
from typing import List

from fast_api_builder.auth.auth import Auth
from fast_api_builder.common.response.codes import ResponseCode
from fast_api_builder.common.response.schemas import ApiResponse

from fastapi import Request
from strawberry import Info
from strawberry.extensions import FieldExtension
from strawberry.fastapi import BaseContext
from graphql import GraphQLError
SESSION_EXPIRED_CODE = "SESSION_EXPIRED"

# Custom GraphQL Context Class
class CustomGraphQLContext(BaseContext):
    def __init__(self, user, auth_error):
        super().__init__()
        self.user = user
        self.auth_error = auth_error


# Context Getter Function
async def get_graphql_context(request: Request) -> CustomGraphQLContext:
    return CustomGraphQLContext(user=request.state.user, auth_error=request.state.auth_error)


# Authentication Permission Check
class IsAuthenticated:
    message = "Unauthorized"

    def has_permission(self, info: Info, **kwargs) -> bool:
        return bool(info.context.user)


# Login Required Extension (Async)
class LoginRequiredExtension(FieldExtension):
    async def resolve_async(self, next_, root, info: Info, **kwargs):
        is_authenticated = IsAuthenticated()
        if not is_authenticated.has_permission(info=info):
            # Return a custom response or raise an error if unauthorized
            if info.context.auth_error == 'EXPIRED':
                raise GraphQLError(
                    "Session expired",
                    extensions={"code": ResponseCode.SESSION_EXPIRED}
                )
                return ApiResponse(
                    code=ResponseCode.SESSION_EXPIRED,
                    status=False,
                    message="Session Expired",
                    data=None,
                )
            
            if info.context.auth_error == 'TOKEN_EXPIRED':
                return ApiResponse(
                    code=ResponseCode.TOKEN_EXPIRED,
                    status=False,
                    message="Token Expired",
                    data=None,
                )
            return ApiResponse(
                code=ResponseCode.UNAUTHORIZED,
                status=False,
                message=IsAuthenticated.message,
                data=None,
            )
        return await next_(root, info, **kwargs)


# Custom Permission Extension (Async)
class CustomPermissionExtension(FieldExtension):
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions

    async def resolve_async(self, next_, root, info: Info, **kwargs):
        user = None
        with contextlib.suppress(Exception):
            user = await Auth.user()

        if user:

            permission_codes = await Auth.user_permissions()

            permissions = list(set(permission_codes))

            has_permission = any(perm in permissions for perm in self.required_permissions)
            if has_permission or user.is_superuser:
                return await next_(root, info, **kwargs)
            else:
                return ApiResponse(
                    code=ResponseCode.RESTRICTED_ACCESS,
                    status=False,
                    message="Restricted Access",
                    data=None,
                )
        else:
            if info.context.auth_error == 'EXPIRED':
                raise GraphQLError(
                    "Session expired",
                    extensions={"code": ResponseCode.SESSION_EXPIRED}
                )
                return ApiResponse(
                    code=ResponseCode.SESSION_EXPIRED,
                    status=False,
                    message="Session Expired",
                    data=None,
                )
            return ApiResponse(
                code=ResponseCode.UNAUTHORIZED,
                status=False,
                message="Unauthorized",
                data=None,
            )
