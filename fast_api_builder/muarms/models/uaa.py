from enum import Enum
from typing import Optional

from passlib.context import CryptContext
from pydantic import BaseModel
from tortoise import fields, models

from fast_api_builder.muarms.models import TimeStampedModel, HeadshipModel, HeadshipType

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

'''List of Models'''


class ContentType(models.Model):
    model = fields.CharField(max_length=255)

    class Meta:
        table = "content_types"
        exclude_from_permissions = True


class DjangoSession(models.Model):
    session_key = fields.CharField(max_length=40, pk=True)
    session_data = fields.TextField()
    expire_date = fields.DatetimeField()
    user_id = fields.IntField()

    class Meta:
        table = "custom_sessions"
        exclude_from_permissions = True


class User(HeadshipModel):
    id = fields.IntField(pk=True)
    last_login = fields.DatetimeField(null=True)
    is_superuser = fields.BooleanField()
    first_name = fields.CharField(max_length=30)
    last_name = fields.CharField(max_length=150)
    is_staff = fields.BooleanField()
    is_active = fields.BooleanField()
    date_joined = fields.DatetimeField()
    username = fields.CharField(max_length=200, unique=True)
    email = fields.CharField(max_length=200, unique=True)
    middle_name = fields.CharField(max_length=200, null=True)
    sex = fields.CharField(max_length=20, null=True)
    title = fields.CharField(max_length=200)
    phone_number = fields.CharField(max_length=30)
    pps_photo = fields.CharField(max_length=100, null=True)
    birth_date = fields.DateField(null=True)
    physical_address = fields.CharField(max_length=300, null=True)
    postal_address = fields.CharField(max_length=300, null=True)
    department = fields.ForeignKeyField("models.Department", related_name="users", null=True)
    country = fields.ForeignKeyField("models.Country", related_name="users")
    is_disabled = fields.BooleanField()
    place_of_birth = fields.CharField(max_length=200, null=True)
    nin = fields.CharField(max_length=200, null=True)
    is_external = fields.BooleanField()
    id_image_uploaded = fields.BooleanField()
    groups = fields.ManyToManyField(
        model_name='models.Group',
        through='user_groups',
        forward_key='group_id',
        backward_key='customuser_id',
        related_name='users')

    class Meta:
        table = "user"
        verbose_name = "User"
        verbose_name_plural = "Users"

    async def get_permissions(self):
        # Get permissions from groups
        group_permissions = await Permission.filter(
            permission_groups__group__group_users__customuser=self
        ).distinct().all()

    def get_short_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.username


class StatusType(models.Model):
    name = fields.CharField(max_length=200, unique=True)

    class Meta:
        db_table = 'status_type'
        verbose_name_plural = 'StatusTypes'


class Status(models.Model):
    name = fields.CharField(max_length=200)
    code = fields.CharField(max_length=200, unique=True)
    status_type = fields.ForeignKeyField('models.StatusType')

    def __str__(self):
        return self.code

    class Meta:
        db_table = 'status'
        verbose_name_plural = 'Statuses'


class Student(models.Model):
    ENTRY_TYPE_CHOICES = [
        ('D', 'Direct'),
        ('E', 'Equivalent'),
    ]

    id = fields.IntField(pk=True)
    registration_number = fields.TextField()
    date_admitted = fields.DateField(null=True)
    user = fields.OneToOneField('models.User', related_name='student', on_delete=fields.CASCADE)
    # district = fields.ForeignKeyField('models.District', related_name='students', null=True)
    programme = fields.ForeignKeyField('models.Programme', related_name='students', null=True)
    status = fields.ForeignKeyField('models.Status', related_name='students', null=True)
    # programme_structure = fields.ForeignKeyField('models.ProgrammeStructure', related_name='students', null=True)
    # exam_by_law = fields.ForeignKeyField('models.ExamByLaws', related_name='students', on_delete=fields.PROTECT, null=True)
    entry_type = fields.CharField(max_length=5, choices=ENTRY_TYPE_CHOICES, null=True)
    current_year_of_study = fields.IntField(default=1)
    application_number = fields.CharField(max_length=50, unique=True, null=True)
    is_extended = fields.BooleanField(default=False)
    is_new_intake = fields.BooleanField(default=False)

    def __str__(self):
        return self.registration_number

    class Meta:
        table = "student"
        verbose_name_plural = "Students"


class Staff(models.Model):
    id = fields.IntField(pk=True)
    pf_number = fields.CharField(max_length=200)
    user = fields.OneToOneField("models.User", on_delete=fields.CASCADE, related_name="staff")

    class Meta:
        table = "staff"
        verbose_name_plural = "Staffs"


class Programme(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=200)
    duration = fields.IntField()
    pass_mark = fields.DecimalField(max_digits=5, decimal_places=2)
    mu_code = fields.CharField(max_length=20, unique=True)
    tcu_code = fields.CharField(max_length=20)
    heslb_code = fields.CharField(max_length=20, null=True)
    entry_point = fields.DecimalField(max_digits=5, decimal_places=2)
    capacity = fields.IntField()
    programme_number = fields.IntField()
    department = fields.ForeignKeyField("models.Department", related_name="programmes", on_delete=fields.CASCADE)
    programme_type = fields.ForeignKeyField("models.ProgrammeType", related_name="programmes", on_delete=fields.CASCADE)

    # mode_of_delivery = fields.CharField(max_length=50)
    # specialization_area = fields.ForeignKeyField("models.SpecializationArea", related_name="programmes", null=True, on_delete=fields.SET_NULL)
    # programme_intake = fields.ForeignKeyField("models.ProgrammeIntake", related_name="programmes", null=True, on_delete=fields.SET_NULL)

    class Meta:
        table = "programme"
        indexes = [
            ("department",),
            ("mu_code",),
            # ("programme_intake",),
            ("programme_type",),
            # ("specialization_area",),
        ]
        constraints = [
            "CHECK (programme_number >= 0)",
        ]

    def __str__(self):
        return self.name


class ProgrammeType(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=200, unique=True)
    programme_type_number = fields.IntField(unique=True)

    class Meta:
        table = "programme_type"
        indexes = [
            ("name",),
        ]
        constraints = [
            "CHECK (programme_type_number >= 0)",
        ]

    def __str__(self):
        return self.name


class Permission(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    codename = fields.CharField(max_length=100)
    content_type_id = fields.IntField()

    class Meta:
        table = "auth_permission"
        unique_together = ("content_type_id", "codename")

    def __str__(self):
        return self.name


class Group(HeadshipModel):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=150, unique=True)
    permissions = fields.ManyToManyField("models.Permission", through="group_permissions")

    class Meta:
        table = "auth_group"
        verbose_name = "Group"
        verbose_name_plural = "Groups"

    def __str__(self):
        return self.name


class GroupPermission(models.Model):
    id = fields.IntField(pk=True)
    group = fields.ForeignKeyField("models.Group", related_name="group_permissions")
    permission = fields.ForeignKeyField("models.Permission", related_name="permission_groups")

    class Meta:
        table = "auth_group_permissions"
        unique_together = ("group", "permission")


class UserGroup(models.Model):
    id = fields.IntField(pk=True)
    customuser = fields.ForeignKeyField(
        "models.User",
        related_name="user_groups",
        on_delete=fields.CASCADE
    )
    group = fields.ForeignKeyField(
        "models.Group",
        related_name="group_users",
        on_delete=fields.CASCADE
    )

    class Meta:
        table = "user_groups"
        unique_together = ("customuser", "group")


class UserStatusLog(TimeStampedModel):
    user = fields.ForeignKeyField('models.User', related_name="status_logs", on_delete=fields.RESTRICT)
    is_active = fields.BooleanField()
    reason = fields.TextField(null=True, blank=True)  # Only needed for deactivation

    def __str__(self):
        status = "Activated" if self.is_active else "Deactivated"
        return f"{self.user.username} {status} on {self.created_at}"

    class Meta:
        table = 'user_status_logs'
        verbose_name = 'User Status Log'
        verbose_name_plural = 'User Status Logs'


# class Headship(TimeStampedModel):
#     user = fields.ForeignKeyField('models.User', related_name="headships", on_delete=fields.RESTRICT)
#     headship_type = fields.CharField(max_length=100)
#     headship_id = fields.UUIDField(max_length=100, null=True)
#     start_date = fields.DateField()
#     end_date = fields.DateField()
#     is_active = fields.BooleanField(default=True)
#
#     created_by = fields.ForeignKeyField(
#         "models.User",
#         null=True,
#         on_delete=fields.SET_NULL,
#         related_name="headships_created"  # Specific related_name to avoid conflict
#     )
#
#     def __str__(self):
#         return f"{self.user.username}: {self.headship_type}"
#
#     class Meta:
#         table = 'headships'
#         verbose_name = 'Headship'
#         verbose_name_plural = 'Headships'


class Headship(BaseModel):
    user: dict
    headship_type: HeadshipType
    headship_id: Optional[int]
    # start_date: date
    # end_date: date
    # is_active: bool
    # programme_ids: list[int] = Field(default_factory=list)
