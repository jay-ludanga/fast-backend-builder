from tortoise import fields
from fast_api_builder.models import TimeStampedModel
from fast_api_builder.utils.config import get_user_model_reference


class Headship(TimeStampedModel):
    user = fields.ForeignKeyField(
        get_user_model_reference(),
        related_name="headships",
        on_delete=fields.RESTRICT,
    )
    headship_type = fields.CharField(max_length=100)
    headship_id = fields.UUIDField(null=True)
    start_date = fields.DateField()
    end_date = fields.DateField()
    is_active = fields.BooleanField(default=True)

    created_by = fields.ForeignKeyField(
        get_user_model_reference(),
        null=True,
        on_delete=fields.SET_NULL,
        related_name="headships_created",
    )

    def __str__(self):
        return f"{self.user.username}: {self.headship_type}"

    class Meta:
        table = "headships"
        verbose_name = "Headship"
        verbose_name_plural = "Headships"
