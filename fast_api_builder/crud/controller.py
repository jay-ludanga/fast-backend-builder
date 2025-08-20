from typing import Generic, Tuple, Type, TypeVar, Optional, List, Dict, Any, Callable
from uuid import UUID

from tortoise.transactions import in_transaction
from tortoise.exceptions import DoesNotExist, FieldError
from tortoise.queryset import QuerySet, Q
from fastapi.encoders import jsonable_encoder
from fast_api_builder.common.request.schemas import PaginationParams
from fast_api_builder.common.response.codes import ResponseCode
from fast_api_builder.common.response.schemas import ApiResponse
from fast_api_builder.common.schemas import CreateSchema, ModelType, ResponseSchema, UpdateSchema

class BaseCRUD(Generic[ModelType, CreateSchema, UpdateSchema]):
    """
    Base class for all CRUD operations using Tortoise ORM.
    """

    def __init__(self, model: Type[ModelType], response_schema: Optional[Type[ResponseSchema]] = None,
                 unique_fields: Optional[List[str]] = None):
        self.model = model
        self.response_schema = response_schema
        self.unique_fields = unique_fields or []  # List of fields that must be unique

    async def check_unique_fields(self, data: Dict[str, Any], exclude_id: Optional[int] = None,
                                  model: Optional[Type[ModelType]] = None) -> None:
        """
        Checks if the fields specified in 'data' are unique in the database.
        """
        if model is None:
            model = self.model
        if not self.unique_fields:
            return  # No unique fields to check

        for field in self.unique_fields:
            if field in data:
                value = data[field]
                queryset = model.filter(**{field: value})
                if exclude_id is not None:
                    queryset = queryset.exclude(id=exclude_id)
                if await queryset.exists():
                    raise ValueError(f"A record with this {field} already exists.")

    async def create(self, obj_in: CreateSchema,
                     condition_function: Optional[Callable[[Dict[str, Any]], ApiResponse]] = None,
                     post_create_function: Optional[Callable[[ModelType, Dict[str, Any]], None]] = None) -> ApiResponse:
        """
        Create an item with optional condition and post-create functions.
        """
        try:
            data = obj_in.dict()

            # Check unique constraints
            await self.check_unique_fields(data)

            # Run the condition function if provided
            if condition_function:
                result = condition_function(data)
                if isinstance(result, ApiResponse):
                    return result
                else:
                    data = result  # Modified data

            # Remove '_removed_fields' if it exists in data
            removed_fields = data.pop('_removed_fields', {})

            # Create the main object
            created_object = await self.model.create(**data)

            # Run the post-create function if provided
            if post_create_function:
                post_create_function(created_object, removed_fields)

            return ApiResponse(
                status=True,
                code=ResponseCode.SUCCESS,
                message=f"{self.model.Meta.verbose_name} created successfully",
            )
        except ValueError as ve:
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=str(ve),
            )
        except Exception as e:
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=f"Failed to create {self.model.Meta.verbose_name}. Try again.",
            )

    async def update(self, obj_in: UpdateSchema,
                     condition_function: Optional[Callable[[Dict[str, Any]], ApiResponse]] = None,
                     post_update_function: Optional[Callable[[ModelType, Dict[str, Any]], None]] = None) -> ApiResponse:
        """
        Update an item by id.
        """
        obj_data = jsonable_encoder(obj_in)
        try:
            obj = await self.model.get(id=obj_in.id)

            # Check unique constraints excluding the current object's id
            await self.check_unique_fields(obj_data, exclude_id=obj.id)

            # Run the condition function if provided
            if condition_function:
                result = condition_function(obj_data)
                if isinstance(result, ApiResponse):
                    return result
                else:
                    obj_data = result  # Modified data

            # Remove '_removed_fields' if it exists in data
            removed_fields = obj_data.pop('_removed_fields', {})

            # Update the object
            await obj.update_from_dict(obj_data).save()

            # Run the post-update function if provided
            if post_update_function:
                post_update_function(obj, removed_fields)

            return ApiResponse(
                status=True,
                code=ResponseCode.SUCCESS,
                message=f"{self.model.Meta.verbose_name} updated successfully",
            )
        except DoesNotExist:
            return ApiResponse(
                status=False,
                code=ResponseCode.NO_RECORD_FOUND,
                message=f"{self.model.Meta.verbose_name} does not exist",
            )
        except ValueError as ve:
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=str(ve),
            )
        except Exception as e:
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=f"Failed to update {self.model.Meta.verbose_name}. Try again {str(e)}"
            )

    async def get(self, id) -> ApiResponse:
        """
        Get a single item by id.
        """
        try:
            obj = await self.model.get(id=id)

            if self.response_schema:
                data =  jsonable_encoder(self.response_schema.model_validate(obj, from_attributes=True))
            else:
                data = obj.to_dict()

            return ApiResponse(
                status=True,
                code=ResponseCode.SUCCESS,
                message=f"{self.model.Meta.verbose_name} fetched successfully",
                data=data
            )
        except DoesNotExist:
            return ApiResponse(
                status=False,
                code=ResponseCode.NO_RECORD_FOUND,
                message=f"{self.model.Meta.verbose_name} does not exist",
            )
        except Exception as e:
            return ApiResponse(
                status=False,
                code=ResponseCode.FAILURE,
                message=f"Failed to retrieve {self.model.Meta.verbose_name}",
            )

    async def get_multiple(self, pagination_params: PaginationParams) -> ApiResponse:
        """
        Get multiple items with pagination, filtering, and sorting.
        """
        try:
            query = self.get_initial_queryset()
            query = self.apply_search_filters(query, pagination_params)
            query = self.apply_filters(query, pagination_params)
            query = self.apply_sorting(query, pagination_params)
            data, count = await self.paginate_data(query, pagination_params)
            return await self.get_final_queryset(data, count)
        except FieldError as e:
            return self.handle_error(e)
        except Exception as e:
            return self.handle_error(e)

    def get_initial_queryset(self) -> QuerySet[ModelType]:
        return self.model.all()

    def apply_search_filters(self, query: QuerySet[ModelType], pagination_params: PaginationParams) -> QuerySet[ModelType]:
        if pagination_params.search and pagination_params.search.query:
            search_filters = Q()
            for column in pagination_params.search.columns:
                if column in self.model._meta.fields:
                    search_filters |= Q(**{f"{column}__icontains": pagination_params.search.query})
            query = query.filter(search_filters)
        return query

    def apply_filters(self, query: QuerySet[ModelType], pagination_params: PaginationParams) -> QuerySet[ModelType]:
        if pagination_params.filters:
            for filter in pagination_params.filters:
                if filter.comparator == 'exclude':
                    query = query.exclude(**{f"{filter.field}": filter.value})
                elif filter.comparator in ['exact', 'icontains', 'startswith', 'endswith', 'contains', 'gte', 'lte', 'ne']:
                    query = query.filter(**{f"{filter.field}__{filter.comparator}": filter.value})
        return query

    def apply_sorting(self, query: QuerySet[ModelType], pagination_params: PaginationParams) -> QuerySet[ModelType]:
        sort_by = pagination_params.sortBy
        sort_order = pagination_params.sortOrder
        model_fields = self.model._meta.fields

        if sort_by and sort_by in model_fields:
            order = '' if sort_order == 'asc' else '-'
            query = query.order_by(f"{order}{sort_by}")
        else:
            query = query.order_by('-id')  # Default ordering by descending ID if sortBy is not provided or invalid

        return query

    async def paginate_data(self, query: QuerySet[ModelType], pagination_params: PaginationParams) -> Tuple:
        offset = (pagination_params.page - 1) * pagination_params.pageSize
        limit = pagination_params.pageSize
        return await query.offset(offset).limit(limit), await query.count()

    async def get_final_queryset(self, data, paginator_count) -> ApiResponse:
        data = list(data)
        if self.response_schema:
            data = [jsonable_encoder(self.response_schema.model_validate(obj, from_attributes=True)) for obj in data]
        else:
            data = [obj.to_dict() for obj in data]
        return ApiResponse(
            status=True,
            code=ResponseCode.SUCCESS,
            message=f"{self.model.Meta.verbose_name_plural} fetched successfully",
            data={
                'items': data,
                'total_count': paginator_count
            }
        )
        
    def delete(self, id) -> ApiResponse:
        """
        Delete an item by id.
        """
        try:
            # Handle the id as either an integer or a UUID
            if isinstance(id, str) and self.is_uuid(id):
                id = UUID(id)
            elif isinstance(id, str) and id.isdigit():
                id = int(id)

            obj = self.model.objects.get(id=id)
            obj.delete()
            return ApiResponse(
                status=True,
                code=ResponseCode.SUCCESS,
                message=f"{self.model._meta.verbose_name} deleted successfully"
            )
        except ObjectDoesNotExist:
            return ApiResponse(
                status=False,
                code=ResponseCode.NO_RECORD_FOUND,
                message=f"{self.model._meta.verbose_name} does not exist",
            )

    def handle_error(self, e: Exception) -> ApiResponse:
        return ApiResponse(
            status=False,
            code=ResponseCode.FAILURE,
            message=f"Error fetching data: {str(e)}",
        )