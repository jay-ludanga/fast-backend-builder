from typing import TypeVar
from tortoise.models import Model
from pydantic import BaseModel


ModelType = TypeVar("ModelType", bound=Model)
CreateSchema = TypeVar("CreateSchema", bound=BaseModel)
UpdateSchema = TypeVar("UpdateSchema", bound=BaseModel)
ResponseSchema = TypeVar("ResponseSchema", bound=BaseModel)