from typing import Optional
import strawberry

from typing import Optional
import strawberry

@strawberry.type
class EvaluationStatusResponse:
    id: Optional[str]
    object_name: Optional[str]
    object_id: Optional[str]
    status: Optional[str]
    remark: Optional[str]
    user_id: Optional[str]
    created_at: Optional[str]
    user_full_name: Optional[str]
