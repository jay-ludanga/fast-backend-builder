"""
 Wrapper class for Connection with GovEsb
"""

import json
import os
from base64 import b64decode, b64encode
import threading
import time
from typing import Callable, Awaitable, Dict, Any, Tuple, Optional
import uuid
import httpx
from cryptography.hazmat.primitives.asymmetric import ec, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
from fast_api_builder.govesb.schemas import GovEsvAckData, GovEsvAckResponse, GovEsvData, GovEsvRequestData, GovEsvRequest, GovEsvResponse
from fast_api_builder.utils.error_logging import log_exception, log_govesb_calls, log_message, log_warning

class GovEsb:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Ensures only one instance of GovEsb is created."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # Double-check locking
                    cls._instance = super(GovEsb, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            # Initialize the attributes only once
            self.client_id = None
            self.client_secret = None
            self.grant_type = None
            self.private_key = None
            self.public_key = None
            self.engine_url = None
            self.token_url = None
            self.timeout = None
            
            self.auth_basic_body = None
            self.access_token = None
            self.token_expiry = None
            
            self.initialized = False

    @classmethod
    async def get_instance(cls):
        """Returns the single instance of GovEsb."""
        if cls._instance is None or not cls._instance.initialized:
            # try to initialize first if params are provided
            if cls._instance and cls._instance.client_id \
                            and cls._instance.client_secret \
                            and cls._instance.grant_type \
                            and cls._instance.token_url:
                log_warning("GovESB service not initialized. Retrying initialization ...")
                if not await cls._instance.request_esb_token():
                    raise Exception("GovEsb service is not initialized.")
            else:
                raise Exception("GovEsb service is not initialized.")
        
        if time.time() >= cls._instance.token_expiry:
            if not await cls._instance.request_esb_token():
                raise Exception("GovEsb token expired. Retry to update")
        
        return cls._instance

    async def init(self, 
            client_id: str, 
            client_secret: str, 
            grant_type: str, 
            private_key: str, 
            public_key: str, 
            engine_url: str, 
            token_url: str, 
            timeout: str = 180
        ):
        """Initialize the GovESB service asynchronously with the given configuration."""
        try:
            if not self.initialized:
                # Initialize the attributes only once
                self.client_id = client_id
                self.client_secret = client_secret
                self.grant_type = grant_type if grant_type else 'client_credentials'
                self.private_key_file = private_key
                self.public_key_file = public_key
                self.engine_url = engine_url
                self.timeout = timeout
                self.token_url = token_url
                self.auth_basic_body = {
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'grant_type': self.grant_type
                }
                
                self.private_key = self.get_private_key_from_pem(self.private_key_file)
                self.public_key = self.get_public_key_from_pem(self.public_key_file)
                
                if await self.request_esb_token():
                    self.initialized = True
                    log_message(f"GovESB initialized successfully")
            else:
                log_warning("GovESB service is already initialized.")
            return True
        except Exception as e:
            log_exception(f"Failed to initialize GovESB: {str(e)}")
            return False

    def basic_auth_header(self):
        token = b64encode(f"{self.client_id}:{self.client_secret}".encode('utf-8')).decode("ascii")
        return {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Basic %s" % token,
        }

    async def request_esb_token(self):
        try:
            # response = requests.post(
            #     url=self.token_url, 
            #     data=self.auth_basic_body,
            #     headers=self.basic_auth_header(),
            #     timeout=self.timeout
            # )
            # response.raise_for_status()
            
            # self.access_token = response.json()['access_token']
            # self.token_expiry = time.time() + response.json()['expires_in'] - 60
            
            # return True
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=self.token_url,
                    data=self.auth_basic_body,
                    headers=self.basic_auth_header(),
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # Process the JSON response
                data = response.json()
                self.access_token = data['access_token']
                self.token_expiry = time.time() + data['expires_in'] - 60
                
                return True
        except Exception as e:
            log_exception(f'GoveESB: Failed to get token {str(e)}')
            return False
        
    @staticmethod
    def get_private_key_from_pem(key):
        """Get the private key from the PEM Key file."""
        if isinstance(key, str):
            key = key.encode("utf-8")
        
        return serialization.load_pem_private_key(key, password=None, backend=default_backend())

    @staticmethod
    def get_private_key_from_base64(key):
        """Get the private key from the base64 content excluding head tags."""
        return serialization.load_der_private_key(b64decode(key), password=None, backend=default_backend())

    @staticmethod
    def get_public_key_from_pem(key):
        """Get the public key from the PEM key file."""
        if isinstance(key, str):
            key = key.encode("utf-8")
        return serialization.load_pem_public_key(key, backend=default_backend())

    @staticmethod
    def get_public_key_from_base64(key):
        """Get the public key from the base64 content excluding head tags."""
        return serialization.load_der_public_key(b64decode(key), backend=default_backend())

    @staticmethod
    def trim_payload(payload):
        """Remove Spaces, Lines from the payload."""
        return json.dumps(payload, separators=(',', ':'))
    
    def sign_payload(self, payload):
        """
        Sign the payload using ECC and return the base64 encoded signature.
        """
        signature = self.private_key.sign(
            self.trim_payload(payload).encode("utf-8"),
            ec.ECDSA(hashes.SHA256()),  # Use ECDSA with SHA256
        )
        return b64encode(signature).decode("utf-8")

    def verify_signature(self, signature, payload):
        """
        Verify the ECC signature of the payload.
        """
        try:
            self.public_key.verify(
                b64decode(signature),  # Decode the base64-encoded signature
                self.trim_payload(payload).encode("utf-8"),
                ec.ECDSA(hashes.SHA256()),  # Use ECDSA with SHA256
            )
            return True  # Signature is valid
        except InvalidSignature:
            return False  # Signature is invalid

    def json_encode(self, data):
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))

    def json_decode(self, data):
        return json.loads(json.dumps(data))

    def build_esb_payload(self, payload, api_code = None, success = None, message = None, errors = None, validation_errors = None):
        """
        Prepare ESB payload for outgoing endpoints.
        @param payload: External Integrated System Payload
        @param api_code: ESB Connection Code
        @return: Object
        """
        data = {
            "esbBody": payload
        }
        
        if api_code:
            data["apiCode"] = api_code
            
        if success is not None:
            data["success"] = success
            
        if message:
            data["message"] = message
            
        if errors:
            data["errors"] = errors
            
        if validation_errors:
            data["validationErrors"] = validation_errors
        
        return {
            "data": data,
            "signature": self.sign_payload(data)
        }

    async def consume(self, payload, api_code) -> GovEsvData:
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=f"{self.engine_url}/request", 
                    # data=self.json_encode(self.build_esb_payload(payload, api_code)),
                    json=self.build_esb_payload(payload, api_code),
                    # json={},
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        'Content-Type': 'application/json'
                    },
                    timeout=self.timeout
                )
            
            response.raise_for_status()
            json = response.json()
            
            log_govesb_calls(
                api_code=api_code,
                request=self.build_esb_payload(payload, api_code),
                response=json
            )
            
            # Verify signature
            if not self.verify_signature(json['signature'], json['data']):
                raise Exception('Signature verification failed!')

            return GovEsvResponse(**json).data
        
        except Exception as e:
            log_exception(Exception(
                (f"Failed to consume: {str(e)}\n"
                f"Request: {str(response.request.content)}\n"
                f"Response: {str(response.content)}\n")
            ))
            return GovEsvData(
                success=False,
                requestId=uuid.uuid4(),
                message=f"Failed to consume from apiCode: {api_code}",
                esbBody={},
                errors=[]
            )

    async def aconsume(
        self, 
        req_body: Dict[str, Any], 
        process_feedback: Callable[[Dict[str, Any]], Awaitable[Tuple[bool, Optional[str], Dict[str, Any]]]]
    ) -> Any:
        """
        Process a GovEsvRequest and return an acknowledgment response.

        This method verifies the signature of the request, processes its `esbBody` 
        asynchronously using a provided callable, and constructs an acknowledgment 
        response using the processed data. If the signature verification fails, it
        returns a failure acknowledgment with a default message.

        Args:
            req_body (GovEsvRequest): 
                The incoming request object containing the data to be processed 
                and its signature for verification.
            
            process_feedback (Callable[[Dict[str, Any]], Awaitable[Tuple[bool, Optional[str], Dict[str, Any]]]]): 
                An asynchronous function that accepts the `esbBody` as a dictionary, 
                processes it, and returns a tuple containing:
                - A boolean indicating success or failure.
                - An optional message string describing the result (can be `None`).
                - A dictionary of processed data.

        Returns:
            GovEsvAckResponse: 
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
            
                response = await Govesb().aconsume(req_body, process_feedback)
            
            3. Return the returned `GovEsvAckResponse` to gov esb:
        """
        # Attempt to verify the signature
        data = req_body.get('data', {})
        if not self.verify_signature(req_body.get('signature', None), data):
            # Build acknowledgment data for failure case
            success = False
            esbBody = {}
            message = "Signature verification failed!"
        else:
            # Process the esbBody asynchronously using the provided callable
            success, message, esbBody = await process_feedback(data.get('esbBody', {}))
            
        # Construct the final acknowledgment response
        esb_payload = self.build_esb_payload(
            payload=esbBody,
            success=success,
            message=message
        )

        log_govesb_calls(
            api_code=None,
            request=esb_payload,
            response=data
        )

        # Return the acknowledgment response
        return esb_payload


    def aproduce(self, payload, api_code):
        pass
    