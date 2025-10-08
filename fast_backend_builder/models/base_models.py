# mypkg/models/base_user.py
from tortoise import fields
from fast_backend_builder.models import TimeStampedModel


class AbstractUser(TimeStampedModel):
    username = fields.CharField(max_length=150, unique=True)
    password = fields.CharField(max_length=255)
    email = fields.CharField(max_length=100, unique=True)
    first_name = fields.CharField(max_length=50)
    middle_name = fields.CharField(max_length=50, null=True)  # Optional
    last_name = fields.CharField(max_length=50)
    phone_number = fields.CharField(max_length=128, null=True)
    groups = fields.ManyToManyField('models.Group', related_name='users', through='user_group')

    class Meta:
        abstract = True  # Important! not registered in DB