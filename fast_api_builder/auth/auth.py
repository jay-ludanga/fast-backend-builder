import asyncio
from datetime import datetime, timedelta
import contextvars

from tortoise import Tortoise

from fast_api_builder.models import HeadshipType
from fast_api_builder.models.group_permissions import Group, Permission
from fast_api_builder.utils.config import get_user_model

# Context variables for request-specific auth data
_user_ctx = contextvars.ContextVar("user_ctx", default=None)
_user_data_ctx = contextvars.ContextVar("user_data_ctx", default=None)
_permissions_ctx = contextvars.ContextVar("permissions_ctx", default=None)
_groups_ctx = contextvars.ContextVar("groups_ctx", default=None)
_student_ctx = contextvars.ContextVar("student_ctx", default=None)
_staff_ctx = contextvars.ContextVar("staff_ctx", default=None)

User = get_user_model()
class Auth:
    @classmethod
    async def init(cls, user_info: dict, user: User = None):
        """Initialize auth for the current request context."""
        _user_data_ctx.set(user_info)
        _user_ctx.set(user)
        _permissions_ctx.set(None)
        _groups_ctx.set(None)

    @classmethod
    async def user(cls) -> User:
        """Get the currently authenticated user."""
        user = _user_ctx.get()
        if not user:
            user_info = _user_data_ctx.get()
            if not user_info:
                return None
            user = await User.get(id=user_info.get("user_id"))
            _user_ctx.set(user)  # Cache it in the current request context
        return user

    @classmethod
    def user_data(cls):
        """Get the current authenticated user data."""
        return user_data if (user_data := _user_data_ctx.get()) else None

    @classmethod
    async def user_permissions(cls):
        """Get all permissions for the authenticated user."""
        permissions = _permissions_ctx.get()
        if permissions is None:
            user = await cls.user()
            permissions = await Permission.filter(
                permission_groups__group__group_users__customuser=user
            ).distinct().values_list("codename", flat=True)
            _permissions_ctx.set(permissions)  # Store in context
        return permissions

    @classmethod
    async def is_staff(cls) -> bool:
        """Check if the user is in the 'staffs' group."""
        user = await cls.user()
        if not user:
            return False
        if (groups := _groups_ctx.get()) is None:
            groups = await Group.filter(group_users__customuser=user).values_list("name", flat=True)
            _groups_ctx.set(groups)
        return "staffs" in groups

    @classmethod
    async def is_student(cls) -> bool:
        """Check if the user is in the 'students' group."""
        user = await cls.user()
        if not user:
            return False
        if (groups := _groups_ctx.get()) is None:
            groups = await Group.filter(group_users__customuser=user).values_list("name", flat=True)
            _groups_ctx.set(groups)
        return "students" in groups



    @classmethod
    async def user_headships(cls, headship_type: HeadshipType):
        """Get all headships for the authenticated user."""
        user_info = _user_data_ctx.get()
        if not user_info:
            return []

        user_id = user_info.get("user_id")
        if not user_id:
            return []

        user = await cls.user()
        if user.is_superuser:
            return [
                Headship(
                    user=user_info,
                    headship_type=HeadshipType.GLOBAL.value,
                    headship_id=None,
                    # start_date=datetime.now() - timedelta(days=1),
                    # end_date=datetime.now() + timedelta(weeks=1),
                    # is_active=True,
                )
            ]
        return [Headship(
            user=user_info,
            headship_type=headship_type.value,
            headship_id=id,

        ) for id in await cls.get_programme_ids_for_user(user_id=user_id)]

    @staticmethod
    async def get_programme_ids_for_user(user_id: int) -> list[int]:
        conn = Tortoise.get_connection("default")
        programme_ids = set()

        # 1. ProgrammeHeadship → Programme
        rows = await conn.execute_query_dict("""
            SELECT DISTINCT ph.programme_id
            FROM programme_headship ph
            JOIN headship h ON ph.headship_ptr_id = h.id
            WHERE h.user_id = $1 AND h.is_active = TRUE
        """, [user_id])
        programme_ids.update(r["programme_id"] for r in rows if r["programme_id"])

        # 2. ProgrammeTypeHeadship → Programme
        rows = await conn.execute_query_dict("""
            SELECT DISTINCT p.id
            FROM programme_type_headship pth
            JOIN headship h ON pth.headship_ptr_id = h.id
            JOIN programme p ON p.programme_type_id = pth.programme_type_id
            WHERE h.user_id = $1 AND h.is_active = TRUE
        """, [user_id])
        programme_ids.update(r["id"] for r in rows)

        # 3. DepartmentHeadship → Programme
        rows = await conn.execute_query_dict("""
            SELECT DISTINCT p.id
            FROM department_headship dh
            JOIN headship h ON dh.headship_ptr_id = h.id
            JOIN programme p ON p.department_id = dh.department_id
            WHERE h.user_id = $1 AND h.is_active = TRUE
        """, [user_id])
        programme_ids.update(r["id"] for r in rows)

        # 4. UnitHeadship → Department → Programme
        rows = await conn.execute_query_dict("""
            SELECT DISTINCT p.id
            FROM unit_headship uh
            JOIN headship h ON uh.headship_ptr_id = h.id
            JOIN department d ON d.unit_id = uh.unit_id
            JOIN programme p ON p.department_id = d.id
            WHERE h.user_id = $1 AND h.is_active = TRUE
        """, [user_id])
        programme_ids.update(r["id"] for r in rows)

        # 5. CampusHeadship → Unit → Department → Programme
        rows = await conn.execute_query_dict("""
            SELECT DISTINCT p.id
            FROM campus_headship ch
            JOIN headship h ON ch.headship_ptr_id = h.id
            JOIN unit u ON u.campus_id = ch.campus_id
            JOIN department d ON d.unit_id = u.id
            JOIN programme p ON p.department_id = d.id
            WHERE h.user_id = $1 AND h.is_active = TRUE
        """, [user_id])
        programme_ids.update(r["id"] for r in rows)

        return list(programme_ids)
