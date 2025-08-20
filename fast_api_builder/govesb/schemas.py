from uuid import UUID
from pydantic import BaseModel
from typing import List, Dict, Optional, Any

class GovEsvData(BaseModel):
    success: bool
    requestId: Optional[UUID] = None
    esbBody: Any = {}
    message: str = None
    errors: List[int] = []
    validationErrors: List[str] = []

class GovEsvResponse(BaseModel):
    data: GovEsvData
    signature: str
    
    
    
class GovEsvRequestData(BaseModel):
    requestId: Optional[UUID] = None
    esbBody: Any
    
class GovEsvRequest(BaseModel):
    data: GovEsvRequestData
    signature: str
    
class GovEsvAckData(BaseModel):
    success: bool
    esbBody: Any = {}
    message: str = None
    errors: List[int] = []
    validationErrors: List[str] = []
    
class GovEsvAckResponse(BaseModel):
    data: GovEsvAckData
    signature: str
    