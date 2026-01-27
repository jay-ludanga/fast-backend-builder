
from pydantic import BaseModel
from typing import List, Optional


import strawberry

@strawberry.input
class Filter:
    field: str
    value: str
    comparator: str


@strawberry.input
class Search:
    query: str
    columns: List[str]
    
    
@strawberry.input
class GroupSchema:
    field: str
    format: Optional[str] = None
    
        
@strawberry.input
class GroupSchemaFunction:
    field: str
    function: str


@strawberry.input
class PaginationParams:
    page: int
    pageSize: int
    sortBy: Optional[str] = "name"
    sortOrder: Optional[str] = "asc"
    groupBy: Optional[List[GroupSchema]] = None
    groupFunctions: Optional[List[GroupSchemaFunction]] = None
    search: Optional[Search] = None
    filters: Optional[List[Filter]] = None
    

class RestFilter(BaseModel):
    field: str
    value: str
    comparator: str


class RestSearch(BaseModel):
    query: str
    columns: List[str]
    
    
class RestGroupSchema(BaseModel):
    field: str
    format: Optional[str] = None
    
        
class RestGroupSchemaFunction(BaseModel):
    field: str
    function: str


class RestPaginationParams(BaseModel):
    page: int
    pageSize: int
    sortBy: Optional[str] = "name"
    sortOrder: Optional[str] = "asc"
    # groupBy: Optional[List[GroupSchema]] = None
    # groupFunctions: Optional[List[GroupSchemaFunction]] = None
    search: Optional[Search] = None
    filters: Optional[List[Filter]] = None

