import uuid
from typing import List, Dict, Any, Tuple

from tortoise import fields, models
from fast_api_builder.muarms.models import TimeStampedModel

class UserActivityLog(models.Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    user_id = fields.UUIDField()
    username = fields.CharField(max_length=200)
    entity = fields.CharField(max_length=255)
    action = fields.CharField(max_length=100)
    details = fields.TextField(null=True)
    action_date = fields.DatetimeField()
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        app = "report"  # Associate this model with the 'report' app
        table = "user_activity_logs"  # Optional: Specify the database table name
        verbose_name = "User Activity Log"
        verbose_name_plural = "User Activity Logs"
