from typing import Optional
import strawberry

from typing import Optional
import strawberry

@strawberry.type
class EvaluationStatusResponse:
    id: Optional[int]
    object_name: Optional[str]
    object_id: Optional[int]
    status: Optional[str]
    remark: Optional[str]
    user_id: Optional[int]
    created_at: Optional[str]
    user_full_name: Optional[str]
