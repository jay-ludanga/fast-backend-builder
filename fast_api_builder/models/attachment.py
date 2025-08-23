import uuid

from tortoise import fields

from fast_api_builder.models import TimeStampedModel


class Attachment(TimeStampedModel):
    title = fields.CharField(max_length=100, null=True)
    description = fields.CharField(max_length=1000, null=True)
    file_path = fields.CharField(max_length=200)
    mem_type = fields.CharField(max_length=45, null=True)
    attachment_type = fields.CharField(max_length=45)
    attachment_type_id = fields.UUIDField(default=uuid.uuid4)
    attachment_type_category = fields.CharField(max_length=45, null=True) # category for particular type


    class Meta:
        table = "attachments"  # Specify the table name if needed

    def __str__(self):
        return f"Attachment {self.id} - {self.file_path}"