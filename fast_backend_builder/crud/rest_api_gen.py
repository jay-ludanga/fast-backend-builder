from typing import List, Optional, Type

from fast_backend_builder.common.request.schemas import GroupSchema, GroupSchemaFunction
from fast_backend_builder.common.response.schemas import ApiResponse, PaginatedResponse
# from fast_backend_builder.crud.templates.graphql_api_template import ResponseType
from fastapi import APIRouter, Depends, Query, UploadFile, File
from pydantic import BaseModel

from fast_backend_builder.attach.gql_controller import AttachmentBaseController
from fast_backend_builder.auth.middleware import authorize
from fast_backend_builder.common.request.schemas import Filter, PaginationParams, Search
from fast_backend_builder.common.validation.decorators import validate_input
from fast_backend_builder.crud.gql_controller import GQLBaseCRUD
from fast_backend_builder.utils.str_helpers import to_snake_case
from fast_backend_builder.workflow.gql_controller import TransitionBaseController
from fast_backend_builder.workflow.request import EvaluationStatus

class ResponseType: pass

def build_crud_endpoints(router: APIRouter, path: str, controller: GQLBaseCRUD,
                         CreateSchema: Type[BaseModel],
                         UpdateSchema: Type[BaseModel]
                         ):
    
    model_verbose = to_snake_case(controller.model.__qualname__)
    
    @router.post(f"{path}/")
    @authorize([f"add_{model_verbose}"])
    @validate_input(CreateSchema)
    def create_item(input_data: CreateSchema):
        return controller.create(input_data)

    @router.post(f"{path}/bulk")
    @authorize([f"add_{model_verbose}"])
    def create_items(items: List[CreateSchema]):
        return controller.create_multiple(items)

    @router.get(f"{path}/{{id}}")
    @authorize([f"view_{model_verbose}"])
    def get_item(id: str):
        return controller.get(id)

    @router.get(f"{path}/")
    @authorize([f"view_{model_verbose}"])
    async def get_items(
        page: int = 1,
        pageSize: int = 10,
        sortBy: Optional[str] = None,
        sortOrder: Optional[str] = None,
        search_query: Optional[str] = None,
        groupBy: Optional[List[str]] = None,
        groupFunctions: Optional[List[str]] = None,
        search_columns: Optional[List[str]] = None,
        filters: Optional[List[str]] = None
    ) -> ApiResponse[PaginatedResponse[ResponseType]]:
        pagination_params = PaginationParams(
            page=page,
            pageSize=pageSize,
            sortBy=sortBy,
            sortOrder=sortOrder,
            groupBy=[
                GroupSchema(
                    field=g.split(',')[0].strip(),
                    format=(g.split(',') + [None])[1].strip() if len(g.split(',')) > 1 else None
                ) for g in groupBy
            ] if groupBy else None,
            groupFunctions=[
                GroupSchemaFunction(
                    field=gf.split(',')[0].strip(),
                    function=gf.split(',')[1].strip()
                ) for gf in groupFunctions
            ] if groupFunctions else None,
            search=Search(
                query=search_query or "",
                columns=search_columns or []
            ) if search_query or search_columns else None,
            filters=[
                Filter(
                    field=f.split(',')[0].strip(),
                    comparator=f.split(',')[1].strip(),
                    value=f.split(',', 2)[2].strip()
                ) for f in filters
            ] if filters else None
        )
        
        fields = [] #resolve_request_fields(info)
        return await controller.get_multiple(pagination_params, fields)

    @router.put(f"{path}/")
    @authorize([f"change_{model_verbose}"])
    def update_item(item: UpdateSchema):
        return controller.update(item)

    @router.put(f"{path}/bulk")
    @authorize([f"change_{model_verbose}"])
    def update_items(items: List[UpdateSchema]):
        return controller.update_multiple(items)

    @router.delete(f"{path}/{{id}}")
    @authorize([f"delete_{model_verbose}"])
    def delete_item(id: str):
        return controller.delete(id)

    @router.delete(f"{path}/bulk")
    @authorize([f"delete_{model_verbose}"])
    def delete_items(ids: List[str]):
        return controller.delete_multiple(ids)

    # Attachment routes
    if isinstance(controller, AttachmentBaseController):
        @router.post(f"{path}/attachments")
        @authorize([f"add_{model_verbose}"])
        def upload_attachment(file: UploadFile = File(...)):
            return controller.upload_attachment(file)

        @router.get(f"{path}/attachments/{{id}}")
        @authorize([f"view_{model_verbose}"])
        def get_attachment(id: str):
            return controller.get_attachment(id)

        @router.delete(f"{path}/attachments/{{id}}")
        @authorize([f"delete_{model_verbose}"])
        def delete_attachment(id: str):
            return controller.delete_attachment(id)

    # Evaluation routes
    if isinstance(controller, TransitionBaseController):
        @router.post(f"{path}/transit")
        @authorize([f"add_{model_verbose}"])
        def transit(data: EvaluationStatus):
            return controller.transit(data)

        @router.get(f"{path}/transitions/{{id}}")
        @authorize([f"view_{model_verbose}"])
        def get_transitions(id: str):
            return controller.get_transitions(id)

    return router

