import base64
from minio import Minio
from minio.commonconfig import CopySource
from minio.error import S3Error
import asyncio
import threading
import aiofiles
from io import BytesIO
from datetime import timedelta

from fast_backend_builder.utils.error_logging import log_exception


class MinioService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MinioService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.minio_client = None
            self.bucket_name = None
            self.initialized = False

    @classmethod
    def get_instance(cls):
        """Get the initialized instance of MinioService."""
        if cls._instance is None or not cls._instance.initialized:
            raise Exception("MinIO service is not initialized.")
        return cls._instance

    async def init(self, server: str, access_key: str, secret_key: str, bucket_name: str, secure: bool = True):
        """Initialize the MinIO service asynchronously with the given configuration."""
        try:
            if not self.initialized:
                self.minio_client = Minio(
                    endpoint=server,
                    access_key=access_key,
                    secret_key=secret_key,
                    secure=secure
                )
                self.bucket_name = bucket_name

                # Ensure bucket exists or create it
                if not self.minio_client.bucket_exists(bucket_name):
                    self.minio_client.make_bucket(bucket_name)

                self.initialized = True
                print(f"MinIO initialized with bucket '{bucket_name}'")
            else:
                print("MinIO service is already initialized.")
            return True
        except S3Error as e:
            log_exception(e)
            return False

    async def upload_file(self, file_name: str, file_data: bytes, content_type: str):
        """Save a file to the MinIO bucket asynchronously and return the file path when successful or False when failed."""
        # Check if MinIO service is initialized
        if not self.initialized:
            print("MinIO service not initialized.")
            return False, 'Files service not initialized'

        try:
            # Use BytesIO to simulate async operation (Minio SDK is not natively async)
            data = BytesIO(file_data)
            await asyncio.to_thread(
                self.minio_client.put_object,
                self.bucket_name,
                file_name,
                data,
                len(file_data),
                content_type=content_type
            )
            print(f"File '{file_name}' saved successfully.")
            file_url = f"{self.bucket_name}/{file_name}"
            return file_url, None  # Return the file path
        except S3Error as e:
            log_exception(e)
            return False, f"Error uploading file '{file_name}'"

    async def delete_file(self, file_name: str):
        """Delete a file from the MinIO bucket asynchronously."""
        if not self.initialized:
            print("MinIO service not initialized.")
            return False, 'Files service not initialized'

        try:
            await asyncio.to_thread(self.minio_client.remove_object, self.bucket_name, file_name)
            print(f"File '{file_name}' deleted successfully.")
            return True
        except S3Error as e:
            log_exception(e)
            return False  # Return False if failed

    async def download_file(self, file_name: str):
        """Download a file from the MinIO bucket asynchronously and return it as base64 bytes."""
        self._ensure_initialized()

        try:
            data = await asyncio.to_thread(self.minio_client.get_object, self.bucket_name, file_name)
            file_bytes = await asyncio.to_thread(data.read)  # Read the entire file into memory

            # Encode the bytes to base64
            base64_bytes = base64.b64encode(file_bytes)

            print(f"File '{file_name}' downloaded successfully as base64.")
            return base64_bytes  # Return the base64-bytes
        except S3Error as e:
            log_exception(e)
            return False  # Return False if failed

    async def download_byte_file(self, file_name: str):
        """
        Download a file from the MinIO bucket asynchronously and return raw bytes.
        """
        self._ensure_initialized()
        try:
            # Fetch file from MinIO
            data = await asyncio.to_thread(self.minio_client.get_object, self.bucket_name, file_name)
            # Read raw bytes
            file_bytes = await asyncio.to_thread(data.read)
            print(f"File '{file_name}' downloaded successfully")
            return file_bytes  # Return raw bytes
        except S3Error as e:
            print(f"Error downloading file: {e}")
            log_exception(e)
            return None

    async def get_signed_url(self, file_name: str, expiry_seconds: int = 3600):
        """
        Generate a pre-signed URL for a file stored in MinIO.

        :param file_name: The name of the file in the bucket.
        :param expiry_seconds: Time in seconds until the URL expires (default is 1 hour).
        :return: A signed URL string or None if an error occurred.
        """
        self._ensure_initialized()

        try:
            url = await asyncio.to_thread(
                self.minio_client.presigned_get_object,
                self.bucket_name,
                file_name,
                expires=timedelta(seconds=expiry_seconds)
            )
            print(f"Generated signed URL for '{file_name}': {url}")
            return url
        except S3Error as e:
            log_exception(e)
            return None


    async def get_file_info_with_signed_url(self, file_name: str, expiry_seconds: int = 3600):
        """
        Retrieve file metadata and a signed download URL from MinIO.

        :param file_name: The name of the file in the bucket.
        :param expiry_seconds: Expiry time (default: 1 hour).
        :return: dict with signed URL, file size, and metadata, or None if error.
        """
        self._ensure_initialized()

        try:
            # Get file metadata
            stat = await asyncio.to_thread(
                self.minio_client.stat_object,
                self.bucket_name,
                file_name
            )

            # Generate signed URL
            signed_url = await asyncio.to_thread(
                self.minio_client.presigned_get_object,
                self.bucket_name,
                file_name,
                expires=timedelta(seconds=expiry_seconds)
            )

            return {
                "file_name": file_name,
                "file_size": stat.size,  # bytes
                "last_modified": stat.last_modified.isoformat(),
                "content_type": stat.content_type,
                "etag": stat.etag,
                "signed_url": signed_url,
                "expires_in": expiry_seconds,
            }

        except S3Error as e:
            log_exception(e)
            return None

    async def rename_folder(self, old_folder: str, new_folder: str):
        """
        Rename/move all objects under old_folder to new_folder.
        Example:
            old_folder = "students/john.doe2025/"
            new_folder = "students/MNMA/BITC9.COB/5335/24/"
        """
        self._ensure_initialized()

        try:
            # List all objects with the prefix (old_folder)
            objects = await asyncio.to_thread(
                lambda: self.minio_client.list_objects(self.bucket_name, prefix=old_folder, recursive=True)
            )

            for obj in objects:
                old_file_name = obj.object_name
                # Replace the old_folder prefix with new_folder
                new_file_name = old_file_name.replace(old_folder, new_folder, 1)

                # Copy old object to new object
                await asyncio.to_thread(
                    self.minio_client.copy_object,
                    self.bucket_name,
                    new_file_name,
                    CopySource(self.bucket_name, old_file_name)  # 👈 FIX
                )

                # Delete old object
                await asyncio.to_thread(
                    self.minio_client.remove_object,
                    self.bucket_name,
                    old_file_name
                )
                print(f"Renamed '{old_file_name}' -> '{new_file_name}'")

            return True, None
        except S3Error as e:
            log_exception(e)
            return False, f"Error renaming folder '{old_folder}' to '{new_folder}'"

    async def rename_file(self, old_file_name: str, new_file_name: str):
        """
        Rename or move a file in the MinIO bucket asynchronously.
        This is done by copying the object to the new name and deleting the old one.
        """
        self._ensure_initialized()

        try:
            # Copy old object to new object
            await asyncio.to_thread(
                self.minio_client.copy_object,
                self.bucket_name,
                new_file_name,  # destination object name
                CopySource(self.bucket_name, old_file_name)  # source object
            )
            # Delete old object
            await asyncio.to_thread(
                self.minio_client.remove_object,
                self.bucket_name,
                old_file_name
            )
            print(f"File renamed from '{old_file_name}' to '{new_file_name}' successfully.")
            return True, None
        except S3Error as e:
            log_exception(e)
            return False, f"Error renaming file '{old_file_name}' to '{new_file_name}'"

    def _ensure_initialized(self):
        """Check if the MinIO service is initialized, else raise an error."""
        if not self.initialized:
            raise Exception("MinIO service is not initialized. Call `init()` first.")
