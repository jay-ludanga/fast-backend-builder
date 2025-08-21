# Group Model
from fast_api_builder.models import TimeStampedModel

from typing import List, Dict, Any, Tuple

from tortoise import fields, models

from fast_api_builder.utils.config import get_user_model_reference


class Group(TimeStampedModel):
    name = fields.CharField(max_length=100, unique=True)
    code = fields.CharField(max_length=100, unique=True)
    permissions = fields.ManyToManyField('models.Permission', related_name='groups', through='group_permission')

    created_by = fields.ForeignKeyField(
        get_user_model_reference(),
        null=True,
        on_delete=fields.SET_NULL,
        related_name="groups_created"  # Specific related_name to avoid conflict
    )

    class Meta:
        table = "groups"
        verbose_name = "Group"
        verbose_name_plural = "Groups"


# Permission Model
class Permission(TimeStampedModel):
    code = fields.CharField(max_length=100, unique=True)
    name = fields.CharField(max_length=100, unique=True)

    created_by = fields.ForeignKeyField(
        get_user_model_reference(),
        null=True,
        on_delete=fields.SET_NULL,
        related_name="permissions_created"  # Specific related_name to avoid conflict
    )

    class Meta:
        table = "permissions"
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"