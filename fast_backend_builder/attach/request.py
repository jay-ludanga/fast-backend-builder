import strawberry
from typing import Optional

@strawberry.input
class AttachmentFile:
    content: str
    content_type: str
    name: str
    extension: str

@strawberry.input
class AttachmentUpload:
    title: Optional[str] = None
    description: Optional[str] = None
    attachment_type_category: Optional[str] = None
    file: AttachmentFile
    