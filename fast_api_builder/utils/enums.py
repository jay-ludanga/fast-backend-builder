# Base Enums where all application using this builder will use and extend to add new enums
import dataclasses

import strawberry
from enum import Enum


@strawberry.enum
class HeadshipType(str, Enum):
    GLOBAL = "Global"


@strawberry.enum
class NotificationChannel(str, Enum):
    EMAIL = "Email",
    SMS = "SMS",
    PUSH = "PUSH"
