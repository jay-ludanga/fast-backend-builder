import json
import threading
import uuid
from base64 import b64encode, b64decode
from typing import Callable, Awaitable, Dict, Any, Optional, Tuple
import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ec
import asyncio
from fast_backend_builder.auth.redis import RedisClient
from fast_backend_builder.esb.schemas import EsbAckResponse, EsbData, EsbRequest, EsbResponse
from fast_backend_builder.utils.error_logging import log_exception, log_esb_calls, log_message, log_warning


class Esb:
    _instance = None
    _lock = threading.Lock()
    _token_lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(Esb, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.redis: Optional[RedisClient] = None
            self.client_id: Optional[str] = None
            self.client_secret: Optional[str] = None
            self.grant_type: Optional[str] = None
            self.private_key: Optional[Any] = None
            self.public_key: Optional[Any] = None
            self.engine_url: Optional[str] = None
            self.token_url: Optional[str] = None
            self.timeout: int = 180
            self.auth_basic_body: Optional[Dict[str, str]] = None
            self.access_token: Optional[str] = None
            self.initialized = False

    @classmethod
    async def get_instance(cls):
        if cls._instance is None or not cls._instance.initialized:
            raise Exception("Esb service is not initialized.")
        return cls._instance

    def _token_key(self):
        return f"esb:token:{self.client_id}"

    async def init(self, redis_cli: RedisClient, client_id: str, client_secret: str, grant_type: str,
                   private_key: str, public_key: str, engine_url: str, token_url: str, timeout: int = 180):
        try:
            if self.initialized:
                log_warning("Esb service is already initialized.")
                return True
            self.redis = redis_cli
            self.client_id = client_id
            self.client_secret = client_secret
            self.grant_type = grant_type or 'client_credentials'
            self.private_key_file = private_key
            self.public_key_file = public_key
            self.engine_url = engine_url
            self.token_url = token_url
            self.timeout = timeout
            self.auth_basic_body = {'client_id': client_id, 'client_secret': client_secret,
                                    'grant_type': self.grant_type}
            self.private_key = self.get_private_key_from_pem(self.private_key_file)
            self.public_key = self.get_public_key_from_pem(self.public_key_file)
            token = await self.redis.get(self._token_key())
            if token:
                self.access_token = token.decode() if isinstance(token, bytes) else token
                log_message("Found existing ESB token in Redis")
            else:
                self.access_token = await self.request_esb_token()
                if not self.access_token:
                    raise Exception("Failed to acquire ESB token during init")
            self.initialized = True
            print("Esb initialized successfully")
            return True
        except Exception as e:
            log_exception(Exception(f"Failed to initialize Esb: {str(e)}"))
            return False

    def basic_auth_header(self):
        token = b64encode(f"{self.client_id}:{self.client_secret}".encode('utf-8')).decode("ascii")
        return {"Content-Type": "application/x-www-form-urlencoded", "Authorization": f"Basic {token}"}

    async def request_esb_token(self) -> Optional[str]:
        try:
            async with httpx.AsyncClient(verify=False, timeout=self.timeout) as client:
                response = await client.post(url=self.token_url,
                                             data={"client_id": self.client_id, "client_secret": self.client_secret,
                                                   "grant_type": self.grant_type}, headers=self.basic_auth_header())
                response.raise_for_status()
                data = response.json()
                access_token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                await self.redis.setex(self._token_key(), expires_in - 60, access_token)
                return access_token
        except Exception as e:
            log_exception(Exception(f"[ESB] Failed to get token: {e}"))
            return None

    async def get_esb_token(self) -> Optional[str]:
        if self.access_token:
            return self.access_token
        async with self._token_lock:
            if self.access_token:
                return self.access_token
            token = await self.redis.get(self._token_key())
            if token:
                self.access_token = token.decode() if isinstance(token, bytes) else token
                return self.access_token
            self.access_token = await self.request_esb_token()
            return self.access_token

    @staticmethod
    def get_private_key_from_pem(key):
        if isinstance(key, str):
            key = key.encode("utf-8")
        return serialization.load_pem_private_key(key, password=None, backend=default_backend())

    @staticmethod
    def get_public_key_from_pem(key):
        if isinstance(key, str):
            key = key.encode("utf-8")
        return serialization.load_pem_public_key(key, backend=default_backend())

    @staticmethod
    def trim_payload(payload):
        return json.dumps(payload, separators=(',', ':'))

    def sign_payload(self, payload):
        signature = self.private_key.sign(self.trim_payload(payload).encode("utf-8"), ec.ECDSA(hashes.SHA256()))
        return b64encode(signature).decode("utf-8")

    def verify_signature(self, signature, payload):
        try:
            self.public_key.verify(b64decode(signature), self.trim_payload(payload).encode("utf-8"),
                                   ec.ECDSA(hashes.SHA256()))
            return True
        except InvalidSignature:
            return False

    def build_esb_payload(self, payload, api_code=None, success=None, message=None, errors=None,
                          validation_errors=None):
        data = {"esbBody": payload}
        if api_code: data["apiCode"] = api_code
        if success is not None: data["success"] = success
        if message: data["message"] = message
        if errors: data["errors"] = errors
        if validation_errors: data["validationErrors"] = validation_errors
        return {"data": data, "signature": self.sign_payload(data)}

    async def consume(self, payload, api_code) -> EsbData:
        try:
            token = await self.get_esb_token()
            if not token: raise Exception("Failed to acquire ESB token")
            async with httpx.AsyncClient() as client:
                response = await client.post(url=f"{self.engine_url}", json=self.build_esb_payload(payload, api_code),
                                             headers={"Authorization": f"Bearer {token}",
                                                      "Content-Type": "application/json"}, timeout=self.timeout)
            response.raise_for_status()
            json_resp = response.json()
            log_esb_calls(api_code=api_code, request=self.build_esb_payload(payload, api_code), response=json_resp)
            if not self.verify_signature(json_resp['signature'], json_resp['data']): raise Exception(
                'Signature verification failed!')
            return EsbResponse(**json_resp).data
        except Exception as e:
            log_exception(Exception(f"Failed to consume: {str(e)}"))
            return EsbData(success=False, requestId=uuid.uuid4(), message=f"Failed to consume from apiCode: {api_code}",
                           esbBody={}, errors=[])

    async def aconsume(self, req_body: Dict[str, Any], process_feedback: Callable[
        [Dict[str, Any]], Awaitable[Tuple[bool, Optional[str], Dict[str, Any]]]]) -> Any:
        """
            Process a EsbRequest and return an acknowledgment response.

            This method verifies the signature of the request, processes its `esbBody`
            asynchronously using a provided callable, and constructs an acknowledgment
            response using the processed data. If the signature verification fails, it
            returns a failure acknowledgment with a default message.

            Args:
                req_body (EsbRequest):
                    The incoming request object containing the data to be processed
                    and its signature for verification.

                process_feedback (Callable[[Dict[str, Any]], Awaitable[Tuple[bool, Optional[str], Dict[str, Any]]]]):
                    An asynchronous function that accepts the `esbBody` as a dictionary,
                    processes it, and returns a tuple containing:
                    - A boolean indicating success or failure.
                    - An optional message string describing the result (can be `None`).
                    - A dictionary of processed data.

            Returns:
                EsbAckResponse:
                    A response object that includes the acknowledgment payload, indicating
                    whether the operation was successful.

            Usage:
                1. Define an asynchronous function to process feedback:

                    async def process_feedback(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Dict[str, Any]]:
                        # Perform some asynchronous operations on the data
                        success = True
                        message = "Processing complete"
                        processed_data = {"processedKey": "processedValue"}
                        return success, message, processed_data

                2. Call the `aconsume` method with the request object and processing function:

                    response = await Esb().aconsume(req_body, process_feedback)

                3. Return the returned `EsbAckResponse` to esb:
        """
        data = req_body.get('data', {})
        if not self.verify_signature(req_body.get('signature', None), data):
            success, esbBody, message = False, {}, "Signature verification failed!"
        else:
            success, message, esbBody = await process_feedback(data.get('esbBody', {}))
        esb_payload = self.build_esb_payload(payload=esbBody, success=success, message=message)
        log_esb_calls(api_code=None, request=esb_payload, response=data)
        return esb_payload

    def aproduce(self, payload, api_code):
        pass
