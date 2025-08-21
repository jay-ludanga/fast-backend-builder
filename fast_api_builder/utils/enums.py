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
    WHATSAPP = "WhatsApp",
    PUSH = "PUSH"
@strawberry.enum
class NotificationContentType(str, Enum):
    PASSWORD_RESET = "Password Reset"
    ACCOUNT_CONFIRMATION = "Account Confirmation"
    PUSH_NOTIFICATION = "PUSH Notification"
    APPLICANT_NOTIFICATION = "Applicant Notification"
    EVALUATOR_NOTIFICATION = "Evaluator Notification"