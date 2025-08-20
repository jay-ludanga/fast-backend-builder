from typing import Optional
import strawberry

from fast_api_builder.attach.request import AttachmentUpload

'''ATTACHMENT_UPLOAD'''
@strawberry.input
class _MODEL_Attachment(AttachmentUpload):
    pass