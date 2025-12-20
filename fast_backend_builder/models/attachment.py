import uuid

from tortoise import fields

from fast_backend_builder.models import TimeStampedModel


class Attachment(TimeStampedModel):
    title = fields.CharField(max_length=200, null=True)
    description = fields.CharField(max_length=1000, null=True)
    file_path = fields.CharField(max_length=200)
    mem_type = fields.CharField(max_length=200, null=True)
    attachment_type = fields.CharField(max_length=200)
    attachment_type_id = fields.UUIDField(default=uuid.uuid4)
    attachment_type_category = fields.CharField(max_length=200, null=True) # category for particular type
    created_by = fields.ForeignKeyField(
        'models.User',
        null=True,
        on_delete=fields.SET_NULL,
        related_name='attachments'
    )


    class Meta:
        table = "attachments"  # Specify the table name if needed
        verbose_name = "Attachment"
        verbose_name_plural = "Attachments"

    def __str__(self):
        return f"Attachment {self.id} - {self.file_path}"