from typing import List, Optional
from strawberry.fastapi import GraphQLRouter
import strawberry
from fastapi import UploadFile, Depends
from src.modules.auth.permission_middleware import get_current_user, authorize
from src.modules.cash.schema import AttachmentCreate
from src.modules.resources.response_code import ResponseCode
from src.modules.resources.schema import ApiResponse

# Define a Strawberry Type for the API Response
@strawberry.type
class AttachmentType:
    id: int
    title: str
    parent_id: int

@strawberry.type
class ApiResponseType:
    status: bool
    code: ResponseCode
    message: str
    data: Optional[AttachmentType] = None


# Define a GraphQL resolver function for uploading a single attachment
@strawberry.mutation
def upload_single_attachment(
    parent_id: int,
    file: UploadFile,
    title: str,
    current_user: dict = Depends(get_current_user),
    controller=Depends()  # Inject the controller
) -> ApiResponseType:
    try:
        attachments = [
            AttachmentCreate(
                parent_id=parent_id,
                title=title,
                content=file
            )
        ]
        controller.upload_attachments(attachments, "parent_id_name")
        return ApiResponseType(status=True, code=ResponseCode.SUCCESS, message="Attachment uploaded successfully.")
    except Exception as e:
        return ApiResponseType(status=False, code=ResponseCode.FAILURE, message="An error occurred while uploading the attachment.")

# Mutation for multiple attachments
@strawberry.mutation
def upload_attachments(
    parent_id: int,
    files: List[UploadFile],
    titles: List[str],
    current_user: dict = Depends(get_current_user),
    controller=Depends()
) -> ApiResponseType:
    try:
        attachments = [
            AttachmentCreate(
                parent_id=parent_id,
                title=titles[i],
                content=files[i]
            )
            for i in range(len(files))
        ]
        controller.upload_attachments(attachments, "parent_id_name")
        return ApiResponseType(status=True, code=ResponseCode.SUCCESS, message="Attachments uploaded successfully.")
    except IndexError:
        return ApiResponseType(status=False, code=ResponseCode.BAD_REQUEST, message="Titles and files count mismatch.")

# Resolver to fetch attachments
@strawberry.type
def get_attachments(parent_id: int, current_user: dict = Depends(get_current_user), controller=Depends()):
    return controller.get_attachments(parent_id, "parent_id_name")

# Resolver to download an attachment
@strawberry.mutation
def download_attachment(attachment_id: int, current_user: dict = Depends(get_current_user), controller=Depends()):
    return controller.download_attachment(attachment_id)

# Resolver to delete an attachment
@strawberry.mutation
def delete_attachment(attachment_id: int, current_user: dict = Depends(get_current_user), controller=Depends()):
    return controller.remove_attachment(attachment_id)


# Combine the queries and mutations into a Strawberry schema
@strawberry.type
class Query:
    get_attachments: List[AttachmentType] = strawberry.field(resolver=get_attachments)

@strawberry.type
class Mutation:
    upload_single_attachment: ApiResponseType = strawberry.mutation(upload_single_attachment)
    upload_attachments: ApiResponseType = strawberry.mutation(upload_attachments)
    download_attachment: ApiResponseType = strawberry.mutation(download_attachment)
    delete_attachment: ApiResponseType = strawberry.mutation(delete_attachment)


# Create the GraphQL router
schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema)










'''Imports'''
from typing import List, Optional
import strawberry
from fastapi import UploadFile, Depends
from tortoise.models import Model
from fast_api_builder.utils.helpers.request import resolve_request_fields
from fast_api_builder.common.request.schemas import Filter, PaginationParams, Search
from fast_api_builder.common.response.schemas import ApiResponse, PaginatedResponse
from fast_api_builder.crud.gql_controller import GQLBaseCRUD

from src.modules.auth.permission_middleware import get_current_user, authorize
from src.modules.cash.schema import AttachmentCreate

# Attachment-specific CRUD controller
controller = GQLBaseCRUD(Model)

# Define Create, Update, and Response Types
@strawberry.input
class AttachmentCreateType:
    parent_id: int
    title: str
    content: UploadFile

@strawberry.input
class AttachmentUpdateType:
    id: int
    title: Optional[str] = None

@strawberry.type
class AttachmentResponseType:
    id: int
    parent_id: int
    title: str

# Queries for fetching attachments
@strawberry.type
class AttachmentQuery:
    @strawberry.field
    async def get_attachment_by_id(self, info, id: str) -> ApiResponse[AttachmentResponseType]:
        fields = resolve_request_fields(info)
        return await controller.get(id, fields)
    
    @strawberry.field
    async def get_all_attachments(self, info,
        page: int = 1,
        pageSize: int = 10,
        sortBy: Optional[str] = None,
        sortOrder: Optional[str] = None,
        search_query: Optional[str] = None,
        search_columns: Optional[List[str]] = None,
        filters: Optional[List[str]] = None
    ) -> ApiResponse[PaginatedResponse[AttachmentResponseType]]:
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
        
        fields = resolve_request_fields(info)
        return await controller.get_multiple(pagination_params, fields)

# Mutations for creating, updating, and deleting attachments
@strawberry.type
class AttachmentMutation:
    @strawberry.mutation
    async def create_attachment(self, input_data: AttachmentCreateType, current_user: dict = Depends(get_current_user)) -> ApiResponse[AttachmentResponseType]:
        # Ensure the user is authorized to create an attachment
        await authorize([f"src.add_attachment"])
        return await controller.create(input_data)

    @strawberry.mutation
    async def update_attachment(self, input_data: AttachmentUpdateType, current_user: dict = Depends(get_current_user)) -> ApiResponse[AttachmentResponseType]:
        # Ensure the user is authorized to update the attachment
        await authorize([f"src.change_attachment"])
        return await controller.update(input_data)

    @strawberry.mutation
    async def delete_attachment(self, id: str, current_user: dict = Depends(get_current_user)) -> ApiResponse[bool]:
        # Ensure the user is authorized to delete the attachment
        await authorize([f"src.delete_attachment"])
        return await controller.delete(id)
        
# Combine Queries and Mutations into Schema
@strawberry.type
class Query:
    attachment: AttachmentQuery = strawberry.field()

@strawberry.type
class Mutation:
    attachment: AttachmentMutation = strawberry.field()

# Build the schema
schema = strawberry.Schema(query=Query, mutation=Mutation)

