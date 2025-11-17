import base64
from io import BytesIO
import os
from typing import Generic, Type, Optional

from tortoise.exceptions import DoesNotExist
from decouple import config
from fast_backend_builder.attach.request import AttachmentUpload
from fast_backend_builder.attach.service import MinioService
from fast_backend_builder.models.attachment import Attachment
from fast_backend_builder.utils.error_logging import log_exception
from minio import Minio
from minio.error import S3Error

from fast_backend_builder.common.response.codes import ResponseCode
from fast_backend_builder.common.response.schemas import ApiResponse, PaginatedResponse
from fast_backend_builder.common.schemas import ModelType


# MinIO setup
class AttachmentBaseController(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def upload_attachment(self, attachment_type_id, attachment: AttachmentUpload) -> ApiResponse:
        try:
            # 1. Check if parent model exists
            obj = await self.model.get(id=attachment_type_id)

            # 2. Get existing attachment (but DO NOT delete yet)
            existing: Optional[Attachment] = await Attachment.filter(
                attachment_type=self.model.__name__,
                attachment_type_id=attachment_type_id,
                attachment_type_category=attachment.attachment_type_category,
            ).first()

            # 3. Decode base64 file
            try:
                decoded_file = base64.b64decode(attachment.file.content)
            except Exception as decode_error:
                return ApiResponse(
                    status=False,
                    code=ResponseCode.FAILURE,
                    message=f"Failed to decode base64 file: {decode_error}",
                    data=None,
                )

            # 4. Build MinIO path for the *new* file
            random_suffix = os.urandom(4).hex()
            file_name = f"{attachment.file.name}_{random_suffix}.{attachment.file.extension}"
            new_object_path = f"{self.model.__name__}/{file_name}"

            # 5. Upload new file to MinIO
            file_location, upload_error = await MinioService.get_instance().upload_file(
                file_name=new_object_path,
                file_data=decoded_file,
                content_type=attachment.file.content_type,
            )

            if not file_location:
                # ❌ New upload failed – do NOT delete the old one
                return ApiResponse(
                    status=False,
                    code=ResponseCode.FAILURE,
                    message=f"File upload failed: {upload_error}",
                    data=None,
                )

            # 6. Now that new upload succeeded, safely remove old file & record (if any)
            if existing:
                try:
                    await MinioService.get_instance().delete_file(existing.file_path)
                except Exception as e:
                    # log, but don't break – new file is already uploaded
                    log_exception(e)

                await existing.delete()

            # 7. Create new attachment record
            try:
                new_attachment = await Attachment.create(
                    title=attachment.title,
                    description=attachment.description,
                    file_path=new_object_path,
                    mem_type=attachment.file.content_type,
                    attachment_type=self.model.__name__,
                    attachment_type_id=attachment_type_id,
                    attachment_type_category=attachment.attachment_type_category,
                )
            except Exception as db_error:
                log_exception(db_error)

                # Optional: rollback the uploaded file from MinIO for consistency
                try:
                    await MinioService.get_instance().delete_file(new_object_path)
                except Exception as e2:
                    log_exception(e2)

                return ApiResponse(
                    status=False,
                    code=ResponseCode.BAD_REQUEST,
                    message=f"Database error: {db_error}",
                    data=None,
                )

            # 8. Success
            return ApiResponse(
                status=True,
                code=ResponseCode.SUCCESS,
                message="File uploaded and saved successfully!",
                data=new_attachment,
            )

        except DoesNotExist:
            return ApiResponse(
                status=False,
                code=ResponseCode.NO_RECORD_FOUND,
                message=f"{self.model.Meta.verbose_name} does not exist",
                data=None,
            )
        except Exception as e:
            log_exception(e)
            return ApiResponse(
                status=False,
                code=ResponseCode.FAILURE,
                message="Unexpected error occurred, try again!",
                data=None,
            )
    async def delete_attachment(self, attachment_id: str) -> ApiResponse:
        try:
            attachment = await Attachment.get(id=attachment_id)
            # Retrieve the file from MinIO
            result = MinioService.get_instance().delete_file(f"{attachment.file_path}")

            await attachment.delete()
            # Return success response with file content
            return ApiResponse(
                status=True,
                code=ResponseCode.SUCCESS,
                message="Attachment deleted successfully!",
                data=result
            )
        except DoesNotExist:
            return ApiResponse(
                status=False,
                code=ResponseCode.NO_RECORD_FOUND,
                message=f"Attachment does not exist",
                data=None
            )
        except Exception as e:
            # Handle errors in file retrieval
            return ApiResponse(
                status=False,
                code=ResponseCode.NO_RECORD_FOUND,
                message=f"An error occurred while deleting the attachment: {e}",
                data=None
            )
            
    async def get_attachments(self, model_id: str) -> ApiResponse:
        try:
            attachments = await Attachment.filter(attachment_type_id=model_id, attachment_type=self.model.__name__)

            return ApiResponse(
                status=True,
                code=ResponseCode.SUCCESS,
                message=f"{self.model.Meta.verbose_name} attachments fetched successfully",
                data=PaginatedResponse(
                    items=attachments,
                    item_count=len(attachments),
                )
            )
        except Exception as e:
            log_exception(Exception(e))
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=f"Failed to fetch {self.model.Meta.verbose_name} attachments. Try again",
                data=None
            )
            
    async def download_attachment(self, file_path: str) -> ApiResponse:
        try:
            # Call the async download_file method to get the base64 content
            base64_content = await MinioService.get_instance().download_file(f"{file_path}")

            if base64_content is False:
                return ApiResponse(
                    status=False,
                    code=ResponseCode.NO_RECORD_FOUND,
                    message="File not found or an error occurred while retrieving the file.",
                    data=None
                )

            # Return success response with base64 content
            return ApiResponse(
                status=True,
                code=ResponseCode.SUCCESS,
                message="File retrieved successfully!",
                data=base64_content.decode('utf-8') # Convert bytes to string
            )

        except Exception as e:
            # Handle errors in file retrieval
            return ApiResponse(
                status=False,
                code=ResponseCode.NO_RECORD_FOUND,
                message=f"An error occurred while retrieving the file: {e}",
                data=None
            )

    async def download_attachment_url(self, file_path: str, expiry_seconds: int = 3600) -> ApiResponse:
        """
        Generate a signed URL for downloading a file from MinIO.

        :param file_path: Relative path to the file in the bucket.
        :param expiry_seconds: Time in seconds for which the signed URL will be valid.
        :return: ApiResponse containing the signed URL or error.
        """
        try:

            signed_url = await MinioService.get_instance().get_signed_url(file_path, expiry_seconds=expiry_seconds)

            if not signed_url:
                return ApiResponse(
                    status=False,
                    code=ResponseCode.NO_RECORD_FOUND,
                    message="Failed to generate signed URL or file does not exist.",
                    data=None
                )

            return ApiResponse(
                status=True,
                code=ResponseCode.SUCCESS,
                message="Signed URL generated successfully!",
                data=signed_url
            )

        except Exception as e:
            return ApiResponse(
                status=False,
                code=ResponseCode.FAILURE,
                message=f"An error occurred while generating signed URL: {e}",
                data=None
            )



