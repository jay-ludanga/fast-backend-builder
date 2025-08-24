import pickle

from tortoise import fields

from fast_api_builder.models import TimeStampedModel
from fast_api_builder.utils.enums import NotificationChannel


class NotificationTemplate(TimeStampedModel):
    name = fields.CharField(max_length=255, unique=True)
    notification_channel = fields.CharEnumField(NotificationChannel, default=NotificationChannel.EMAIL)
    # Dynamic content type (like PASSWORD_RESET, ACCOUNT_CONFIRMATION, INVOICE_CREATED, etc.)
    content_type = fields.CharField(
        max_length=100,
        description="Dynamic string identifier (e.g., PASSWORD_RESET, ACCOUNT_CONFIRMATION)"
    )
    content = fields.TextField()
    args_schema = fields.JSONField(null=True)
    is_active = fields.BooleanField(default=True)  # Use is_active instead of status

    created_by = fields.ForeignKeyField(
        'models.User',
        null=True,
        on_delete=fields.SET_NULL,
        related_name="notification_templates_created"  # Specific related_name to avoid conflict
    )

    class Meta:
        table = "notification_templates"
        verbose_name = "Notification Template"
        verbose_name_plural = "Notification Templates"

    def __str__(self):
        return f"{self.name}"

    async def save(self, *args, **kwargs):
        # Check if the current instance is active
        if self.is_active:
            # Deactivate all other active templates with the same content_type and notification_channel
            await NotificationTemplate.filter(
                content_type=self.content_type,
                notification_channel=self.notification_channel,
                is_active=True
            ).update(is_active=False)

        # Save the current instance
        await super().save(*args, **kwargs)


class FailedTask(TimeStampedModel):
    """
    Model class for Failed Task for Retrying
    """
    name = fields.CharField(max_length=255)
    func = fields.CharField(max_length=255)
    args = fields.BinaryField()  # Using BinaryField for storing pickled data
    result = fields.TextField()

    def set_args(self, args):
        self.args = pickle.dumps(args)  # Serializing the arguments

    def get_args(self):
        return pickle.loads(self.args)  # Deserializing the arguments

    def __str__(self):
        return f"FailedTask(name={self.name}, func={self.func})"

    class Meta:
        table = "failed_task"
        verbose_name = "Failed Task"
        verbose_name_plural = "Failed Tasks"
