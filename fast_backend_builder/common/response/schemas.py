
import strawberry
from pydantic import BaseModel
from typing import Dict, Generic, List, Optional, TypeVar

T = TypeVar("T")

@strawberry.type
class ErrorDetail:
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
    field: str
    message: str

@strawberry.type
class ApiResponse(Generic[T]):
    status: bool
    code: int
    message: str
    errors: Optional[List[ErrorDetail]] = None
    data: Optional[T] = None

@strawberry.type
class PaginatedResponse(Generic[T]):
    item_count: int
    items: list[T]
    
    
class RestErrorDetail(BaseModel):
    # def __init__(self, field: str, message: str):
    #     self.field = field
    #     self.message = message
    field: str
    message: str

class RestApiResponse(BaseModel, Generic[T]):
    status: bool
    code: int
    message: str
    errors: Optional[List[ErrorDetail]] = None
    data: Optional[T] = None

class RestPaginatedResponse(BaseModel, Generic[T]):
    item_count: int
    items: list[T]
