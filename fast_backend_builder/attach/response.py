from typing import Optional
import strawberry

from typing import Optional
import strawberry

@strawberry.type
class AttachmentResponse:
    id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    file_path: Optional[str] = None
    mem_type: Optional[str] = None
    attachment_type: Optional[str] = None
    attachment_type_category: Optional[str] = None
    attachment_type_id: Optional[int] = None
