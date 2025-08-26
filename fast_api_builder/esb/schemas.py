from typing import List, Optional, Any
from uuid import UUID

from pydantic import BaseModel


class EsbData(BaseModel):
    success: bool
    requestId: Optional[UUID] = None
    esbBody: Any = {}
    message: str = None
    errors: List[int] = []
    validationErrors: List[str] = []

class EsbResponse(BaseModel):
    data: EsbData
    signature: str
    
    
    
class EsbRequestData(BaseModel):
    requestId: Optional[UUID] = None
    esbBody: Any
    
class EsbRequest(BaseModel):
    data: EsbRequestData
    signature: str
    
class EsbAckData(BaseModel):
    success: bool
    esbBody: Any = {}
    message: str = None
    errors: List[int] = []
    validationErrors: List[str] = []
    
class EsbAckResponse(BaseModel):
    data: EsbAckData
    signature: str
    