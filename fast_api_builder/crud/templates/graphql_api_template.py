class CreateType: pass
class UpdateType: pass
class ResponseType: pass
from tortoise.models import Model

'''Imports'''
from typing import List, Optional
from fast_api_builder.utils.helpers.request import resolve_request_fields
import strawberry

from fast_api_builder.auth.context import CustomPermissionExtension
from fast_api_builder.common.request.schemas import Filter, Group, GroupFunction, PaginationParams, Search
from fast_api_builder.common.response.schemas import ApiResponse, PaginatedResponse
from fast_api_builder.crud.gql_controller import GQLBaseCRUD
from fast_api_builder.attach.response import _MODEL_AttachmentResponse
from fast_api_builder.attach.request import _MODEL_Attachment
from fast_api_builder.workflow.response import _MODEL_EvaluationStatusResponse
from fast_api_builder.workflow.request import EvaluationStatus
from fast_api_builder.common.validation.decorators import validate_input

controller = GQLBaseCRUD(Model)

@strawberry.type
class _MODEL_Query:
    @strawberry.field(extensions=[CustomPermissionExtension(['view__flatmodel_'])])
    async def get__model__by_id(self, info, id: int) -> ApiResponse[ResponseType]:
        fields = resolve_request_fields(info)
        return await controller.get(id, fields)
    
    @strawberry.field(extensions=[CustomPermissionExtension(['view__flatmodel_'])])
    async def get_all__models_(self, info,
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
                Group(
                    field=g.split(',')[0].strip(),
                    format=(g.split(',') + [None])[1].strip() if len(g.split(',')) > 1 else None
                ) for g in groupBy
            ] if groupBy else None,
            groupFunctions=[
                GroupFunction(
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
                    value=f.split(',')[2].strip()
                ) for f in filters
            ] if filters else None
        )
        
        fields = resolve_request_fields(info)
        return await controller.get_multiple(pagination_params, fields)
    
    '''ATTACHMENT_QUERIES'''
    @strawberry.field(extensions=[CustomPermissionExtension(['view__flatmodel__attachments'])])
    async def get__model__attachments(self, _model__id: str) -> ApiResponse[PaginatedResponse[_MODEL_AttachmentResponse]]:
        return await controller.get_attachments(_model__id)

    @strawberry.field(extensions=[CustomPermissionExtension(['download__flatmodel__attachment'])])
    async def download__model__attachment(self, file_path: str) -> ApiResponse[str]:
        return await controller.download_attachment(file_path)
    '''ATTACHMENT_QUERIES_END'''
    
    '''EVALUATION_QUERIES'''
    @strawberry.field(extensions=[CustomPermissionExtension(['view__flatmodel__transitions'])])
    async def get__model__transitions(self, _model__id: str) -> ApiResponse[PaginatedResponse[_MODEL_EvaluationStatusResponse]]:
        return await controller.get_transitions(_model__id)
    '''EVALUATION_QUERIES_END'''


@strawberry.type
class _MODEL_Mutation:
    
    @strawberry.mutation(extensions=[CustomPermissionExtension(['add__flatmodel_'])])
    @validate_input(CreateType)
    async def create__model_(self, input_data: CreateType) -> ApiResponse[ResponseType]:
        return await controller.create(input_data)
    
    '''CREATE_MULTIPLE'''
    @strawberry.mutation(extensions=[CustomPermissionExtension(['add__flatmodel_'])])
    @validate_input(CreateType)
    async def create__models_(self, input_data: List[CreateType]) -> ApiResponse[List[ResponseType]]:
        return await controller.create_multiple(input_data)
    '''CREATE_MULTIPLE_END'''
    
    @strawberry.mutation(extensions=[CustomPermissionExtension(['change__flatmodel_'])])
    @validate_input(UpdateType)
    async def update__model_(self, input_data: UpdateType) -> ApiResponse[ResponseType]:
        return await controller.update(input_data)

    @strawberry.mutation(extensions=[CustomPermissionExtension(['delete__flatmodel_'])])
    async def delete__model_(self, id: int) -> ApiResponse[bool]:
        return await controller.delete(id)
    
    '''ATTACHMENT_MUTATIONS'''
    @strawberry.mutation(extensions=[CustomPermissionExtension(['upload__flatmodel__attachment'])])
    @validate_input(_MODEL_Attachment)
    async def upload__model__attachment(self, input_data: _MODEL_Attachment, _model__id: int) -> ApiResponse[_MODEL_AttachmentResponse]:
        return await controller.upload_attachment(_model__id, input_data)

    @strawberry.mutation(extensions=[CustomPermissionExtension(['delete__flatmodel__attachment'])])
    async def delete__model__attachment(self, attachment_id: int) -> ApiResponse[bool]:
        return await controller.delete_attachment(attachment_id)
    '''ATTACHMENT_MUTATIONS_END'''
    
    '''EVALUATION_MUTATIONS'''
    @strawberry.mutation(extensions=[CustomPermissionExtension(['transit__flatmodel_'])])
    @validate_input(EvaluationStatus)
    async def transit__model_(self, input_data: EvaluationStatus) -> ApiResponse[bool]:
        return await controller.transit(input_data)
    '''EVALUATION_MUTATIONS_END'''