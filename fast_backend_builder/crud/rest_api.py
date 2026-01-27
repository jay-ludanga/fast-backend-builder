from typing import List, Optional, Type

# from fast_backend_builder.crud.templates.graphql_api_template import ResponseType
from fast_backend_builder.attach.gql_controller import AttachmentBaseController
from fast_backend_builder.common.request.schemas import RestFilter, RestGroupSchema, RestGroupSchemaFunction, RestPaginationParams, RestSearch
from fast_backend_builder.common.response.schemas import RestApiResponse, RestPaginatedResponse
from fast_backend_builder.workflow.gql_controller import TransitionBaseController
from fast_backend_builder.workflow.request import EvaluationStatus
from fastapi import APIRouter, Depends, UploadFile, File, Query
from pydantic import BaseModel

from fast_backend_builder.auth.middleware import authorize, get_current_user
from fast_backend_builder.common.validation.decorators import validate_input
from fast_backend_builder.crud.gql_controller import GQLBaseCRUD
from fast_backend_builder.utils.str_helpers import to_snake_case

# class ResponseType(BaseModel): pass

def build_crud_endpoints(appRouter: APIRouter, path: str, 
                         controller: GQLBaseCRUD,
                         CreateSchema: Type[BaseModel],
                         UpdateSchema: Type[BaseModel],
                         ResponseType: Type[BaseModel],
                         has_attachments: bool = False,
                         has_workflow: bool = False,
                         tags: Optional[List[str]] = None,
                         security_dependency=Depends(get_current_user)
                         ):
    
    model_verbose = to_snake_case(controller.model.__qualname__)
    
    router = APIRouter(
        prefix=path,
        tags=tags
    )
    
    @router.post(f"{path}")
    @authorize([f"add_{model_verbose}"])
    @validate_input(CreateSchema)
    def create_item(input_data: CreateSchema, current_user: dict = security_dependency):
        return controller.create(input_data)
    
    @router.post(f"{path}/bulk")
    @authorize([f"add_{model_verbose}"])
    @validate_input(CreateSchema)
    def create_items(input_data: List[CreateSchema], current_user: dict = security_dependency):
        return controller.create_multiple(input_data)
    
    @router.get(f"{path}/{{id}}")
    @authorize([f"view_{model_verbose}"])
    def get_item(id: str, current_user: dict = security_dependency):
        return controller.get(id)
    
    @router.get(f"{path}")
    @authorize([f"view_{model_verbose}"])
    async def get_items(
        page: int = 1,
        pageSize: int = 10,
        sortBy: Optional[str] = Query(None),
        sortOrder: Optional[str] = Query(None),
        search_query: Optional[str] = Query(None),
        search_columns: Optional[List[str]] = Query(None),
        filters: Optional[List[str]] = Query(None),
        current_user: dict = security_dependency
    ) -> RestApiResponse[RestPaginatedResponse[ResponseType]]:
        pagination_params = RestPaginationParams(
            page=page,
            pageSize=pageSize,
            sortBy=sortBy,
            sortOrder=sortOrder,
            search=RestSearch(
                query=search_query or "",
                columns=search_columns or []
            ) if search_query or search_columns else None,
            filters=[
                RestFilter(
                    field=f.split(',')[0].strip(),
                    comparator=f.split(',')[1].strip(),
                    value=f.split(',', 2)[2].strip()
                ) for f in filters
            ] if filters else None
        )
        
        fields = [] #resolve_request_fields(info)
        return await controller.get_multiple(pagination_params, fields)

    @router.put(f"{path}")
    @authorize([f"change_{model_verbose}"])
    def update_item(item: UpdateSchema, current_user: dict = security_dependency):
        return controller.update(item)

    @router.put(f"{path}/bulk")
    @authorize([f"change_{model_verbose}"])
    def update_items(items: List[UpdateSchema], current_user: dict = security_dependency):
        return controller.update_multiple(items)

    @router.delete(f"{path}/{{id}}")
    @authorize([f"delete_{model_verbose}"])
    def delete_item(id: str, current_user: dict = security_dependency):
        return controller.delete(id)

    @router.delete(f"{path}/bulk")
    @authorize([f"delete_{model_verbose}"])
    def delete_items(ids: List[str], current_user: dict = security_dependency):
        return controller.delete_multiple(ids)

    # Attachment routes
    if has_attachments:
        @router.post(f"{path}/attachments")
        @authorize([f"add_{model_verbose}"])
        def upload_attachment(file: UploadFile = File(...), current_user: dict = security_dependency):
            return controller.upload_attachment(file)

        @router.get(f"{path}/attachments/{{id}}")
        @authorize([f"view_{model_verbose}"])
        def get_attachment(id: str, current_user: dict = security_dependency):
            return controller.get_attachment(id)

        @router.delete(f"{path}/attachments/{{id}}")
        @authorize([f"delete_{model_verbose}"])
        def delete_attachment(id: str, current_user: dict = security_dependency):
            return controller.delete_attachment(id)

    # Evaluation routes
    if has_workflow:
        @router.post(f"{path}/transit")
        @authorize([f"add_{model_verbose}"])
        def transit(data: EvaluationStatus, current_user: dict = security_dependency):
            return controller.transit(data)

        @router.get(f"{path}/transitions/{{id}}")
        @authorize([f"view_{model_verbose}"])
        def get_transitions(id: str, current_user: dict = security_dependency):
            return controller.get_transitions(id)

    appRouter.include_router(router)
    return router

