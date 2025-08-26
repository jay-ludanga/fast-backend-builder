import asyncio
from contextvars import ContextVar
from datetime import datetime, timedelta

from fast_backend_builder.models.headship import Headship
from fast_backend_builder.utils.config import get_user_model
from fast_backend_builder.utils.enums import HeadshipType

User = get_user_model()


class Auth:
    _user_data: ContextVar[dict | None] = ContextVar("user_data", default=None)
    _user: ContextVar[User | None] = ContextVar("_user", default=None)
    _permissions: ContextVar[dict | None] = ContextVar("permissions", default=None)
    _groups: ContextVar[dict | None] = ContextVar("groups", default=None)
    _initialized: ContextVar[bool | None] = ContextVar("initialized", default=False)

    @classmethod
    async def init(cls, user_info: dict, permissions: dict = {}, groups: dict = {}):
        """
        Asynchronously initialize the Auth service with user information, permissions, and groups.

        This method should be called once during the request lifecycle, typically in middleware.
        After initialization, the auth data can be accessed globally via the class methods.

        Args:
            user_info (dict): Information about the authenticated user (e.g., ID, name).
            permissions (dict): A dictionary mapping user IDs to their respective permissions.
            groups (dict): A dictionary mapping user IDs to their respective group memberships.
        """
        cls._user_data.set(user_info)
        cls._permissions.set(permissions)
        cls._groups.set(groups)
        cls._initialized.set(True)

    @classmethod
    def user(cls):
        """
        Get the current authenticated user data.

        This method returns the user data that was passed during initialization.
        Raises an exception if the Auth service has not been initialized.

        Returns:
            dict: The current user data (e.g., {"id": "user123", "name": "John Doe"}).
        """
        cls._ensure_initialized()
        return cls._user_data.get()

    @classmethod
    async def user_object(cls):
        """
        Get the current authenticated user object.

        This method returns the user object that was passed during initialization.
        Raises an exception if the Auth service has not been initialized.

        Returns:
            User: The current user object.
        """
        cls._ensure_initialized()

        if cls._user.get():
            return cls._user.get()

        user_id = cls.user().get('user_id')

        if not user_id:
            return None

        cls._user.set(await User.get(id=user_id))

        return cls._user.get()

    @classmethod
    async def user_can(cls, permissions: str | list):
        """
        Check if the authenticated user has the given permission.

        Use this method to check if the current user is allowed to perform a certain action.
        The permissions should have been passed during the initialization phase.

        Args:
            permission (str): The permission string to check (e.g., "read", "write").

        Returns:
            bool: True if the user has the given permission, False otherwise.
        """
        cls._ensure_initialized()
        if isinstance(permissions, str):
            permissions = [permissions]

        user_id = cls.user().get('user_id')

        if not user_id:
            return False

        user: User = await User.get(id=user_id)

        if not user:
            return False

        has_permission = any(perm in await cls.user_permissions() for perm in permissions)

        return has_permission or user.is_superuser

    @classmethod
    async def user_groups(cls):
        """
        Get the groups the authenticated user belongs to.

        Use this method to retrieve the groups the current user is a member of.
        The groups data should have been passed during the initialization phase.

        Returns:
            list: A list of groups the user belongs to (e.g., ["admin", "editor"]).
        """
        cls._ensure_initialized()
        if cls._groups.get():
            return cls._groups.get()

        user_id = cls.user().get('user_id')

        if not user_id:
            return []

        user: User = await User.get(id=user_id)

        if user:
            # Query the permission codes directly using .values_list() across the user's groups
            cls._groups.set(await user.groups.all())

        return cls._groups.get()

    @classmethod
    async def user_permissions(cls):
        """
        Get all the permissions for the authenticated user.

        This method returns a list of permissions associated with the user.
        It allows you to see all the actions the user is authorized to perform.

        Returns:
            list: A list of permissions (e.g., ["read", "write", "delete"]).
        """
        cls._ensure_initialized()
        if cls._permissions.get():
            return cls._permissions.get()

        user_id = cls.user().get('user_id')

        if not user_id:
            return []

        user: User = await User.get(id=user_id)

        if user:
            # Query the permission codes directly using .values_list() across the user's groups
            permission_codes = await user.groups.all().values_list('permissions__code', flat=True)

            # Return unique permission codes as a list
            cls._permissions.set(list(set(permission_codes)))

        return cls._permissions.get()

    @classmethod
    async def user_headships(cls, headship_type: HeadshipType):
        """
        Get all the permissions for the authenticated user.

        This method returns a list of permissions associated with the user.
        It allows you to see all the actions the user is authorized to perform.

        Returns:
            list: A list of permissions (e.g., ["read", "write", "delete"]).
        """
        cls._ensure_initialized()

        user_id = cls.user().get('user_id')

        if user_id:
            if not cls._user.get():
                cls._user.set(await User.get(id=user_id))

            if cls._user.get():
                if cls._user.get().is_superuser:
                    return [Headship(
                        user=cls._user.get(),
                        headship_type=HeadshipType.GLOBAL.value,
                        headship_id=None,
                        start_date=datetime.now() - timedelta(days=1),
                        end_date=datetime.now() + timedelta(weeks=1),
                        is_active=True
                    )]

                return await Headship.filter(user_id=user_id,
                                             headship_type__in=[HeadshipType.GLOBAL.value, headship_type.value],
                                             is_active=True).all()

        return []

        # return await cls._permissions.get(user_id, [])

    @classmethod
    def _ensure_initialized(cls):
        """
        Ensure the Auth service has been initialized.

        This private method is used internally to verify that the service is initialized before
        any user-related data is accessed. If not initialized, it raises an exception.

        Raises:
            Exception: If the Auth service is not initialized.
        """
        if not cls._initialized.get():
            raise Exception("Auth service is not initialized. Call `Auth.init()` first.")
