from tortoise import fields
from tortoise.models import Model

'''List of Models'''
class _MODEL_(TimeStampedModel):
    name = fields.CharField(max_length=100 ,unique=True)