from typing import Optional
import strawberry

from typing import Optional
import strawberry

from fast_backend_builder.attach.service import MinioService


@strawberry.type
class AttachmentResponse:
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    file_path: Optional[str] = None
    mem_type: Optional[str] = None
    attachment_type: Optional[str] = None
    attachment_type_category: Optional[str] = None
    attachment_type_id: Optional[str] = None

    @strawberry.field
    async def signed_url(self) -> Optional[str]:
        # 'self' here refers to the instance of AttachmentResponse
        # that was created from the source Attachment object.
        if self.file_path:
            # You resolve the value asynchronously right here
            return await MinioService().get_instance().get_signed_url(self.file_path)
        return None
