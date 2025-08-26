import strawberry
from typing import Optional

@strawberry.input
class EvaluationStatus:
    object_id: int
    status: str
    remark: Optional[str] = None