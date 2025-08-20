
import base64
from minio import Minio
from minio.error import S3Error
import asyncio
import threading
import aiofiles
from io import BytesIO
from datetime import timedelta

from fast_api_builder.utils.error_logging import log_exception

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

    def _ensure_initialized(self):
        """Check if the MinIO service is initialized, else raise an error."""
        if not self.initialized:
            raise Exception("MinIO service is not initialized. Call `init()` first.")
