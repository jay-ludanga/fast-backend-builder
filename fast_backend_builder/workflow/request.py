import strawberry
from typing import Optional

@strawberry.input
class EvaluationStatus:
    object_id: str
    status: str
    remark: Optional[str] = None