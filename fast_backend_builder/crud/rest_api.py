from typing import List, Optional, Type
from fastapi import APIRouter, Depends
from fastapi.params import Query
from pydantic import BaseModel

from fast_backend_builder.common.request.schemas import Filter, PaginationParams, Search

# from src.modules.auth.permission_middleware import authorize, get_current_user
# from src.modules.resources.schema import Filter, PaginationParams, Search

def build_rest_crud(router: APIRouter, path: str, controller,
                         CreateSchema: Type[BaseModel],
                         UpdateSchema: Type[BaseModel]
                         ):

    @router.post(f"{path}/")
    # @authorize([f"{app_name}.add_{model_verbose}"])
    def create_item(item: CreateSchema):
        return controller.create(item)

    @router.get(f"{path}/{{id}}")
    # @authorize([f"{app_name}.view_{model_verbose}"])
    def get_item(id: str):
        return controller.get(id)

    @router.get(f"{path}/")
    # @authorize([f"{app_name}.view_{model_verbose}"])
    def get_items(
            page: int = Query(1, description="Page number for pagination"),
            pageSize: int = Query(10, description="Number of items per page"),
            sortBy: Optional[str] = Query(None, description="Field to sort by"),
            sortOrder: Optional[str] = Query(None, description="Order of sorting (asc or desc)"),
            search_query: Optional[str] = Query(None, description="The search string"),
            search_columns: Optional[List[str]] = Query(None, description="List of columns to search in"),
            filters: Optional[List[str]] = Query(None, description="list of field, comparator, value for filtering"),
    ):
        pagination_params = PaginationParams(
            page=page,
            pageSize=pageSize,
            sortBy=sortBy,
            sortOrder=sortOrder,
            search=Search(
                query=search_query or "",
                columns=search_columns or []
            ) if search_query or search_columns else None,
            filters=[
                Filter(
                    field=f.split(',')[0].strip(),
                    comparator=f.split(',')[1].strip(),
                    value=f.split(',')[2].strip()
                ) for f in filters
            ] if filters else None
        )
        return controller.get_multiple(pagination_params)

    @router.put(f"{path}/")
    # @authorize([f"{app_name}.change_{model_verbose}"])
    def update_item(item: UpdateSchema):
        return controller.update(item)

    @router.delete(f"{path}/{{id}}")
    # @authorize([f"{app_name}.delete_{model_verbose}"])
    def delete_item(id: str,):
        return controller.delete(id)

    return router
