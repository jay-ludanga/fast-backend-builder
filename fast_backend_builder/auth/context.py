from typing import List

from fast_backend_builder.common.response.codes import ResponseCode
from fast_backend_builder.common.response.schemas import ApiResponse

from fastapi import Request
from strawberry import Info
from strawberry.extensions import FieldExtension
from strawberry.fastapi import BaseContext

from fast_backend_builder.utils.config import get_user_model

User = get_user_model()

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
                return ApiResponse(
                    code=ResponseCode.SESSION_EXPIRED,
                    status=False,
                    message="Session Expired",
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
        user = info.context.user
        if user:
            # Check if the user has the required permissions
            user_obj = await User.filter(id=user.get('user_id')).prefetch_related('groups__permissions').get_or_none()
            if not user_obj:
                return ApiResponse(
                    code=ResponseCode.UNAUTHORIZED,
                    status=False,
                    message="Unauthorized",
                    data=None,
                )

            # Now you can use `user_obj` which already has the prefetched data
            user: User = user_obj

            # Query the permission codes directly using .values_list() across the user's groups
            permission_codes = await user.groups.all().values_list('permissions__code', flat=True)

            # Return unique permission codes as a list
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
