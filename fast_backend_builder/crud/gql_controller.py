import inspect
import json
from datetime import datetime, date
from enum import Enum
from typing import Generic, Tuple, Type, TypeVar, Optional, Dict, Any, Callable, List, Awaitable
from uuid import UUID

from fast_backend_builder.utils.enums import APIType
from tortoise import fields
from tortoise.exceptions import DoesNotExist, FieldError, IntegrityError, ValidationError
from tortoise.queryset import QuerySet, Q
from tortoise.fields.relational import ForeignKeyFieldInstance, ManyToManyFieldInstance

from tortoise.expressions import F as FExpression
from tortoise.functions import Function, Count, Sum, Avg, Min, Max, Concat
import re
import pytz
from fastapi.encoders import jsonable_encoder

from fast_backend_builder.auth.auth import Auth
from fast_backend_builder.common.request.schemas import PaginationParams
from fast_backend_builder.common.response.codes import ResponseCode
from fast_backend_builder.common.response.schemas import ApiResponse, PaginatedResponse
from fast_backend_builder.common.schemas import ModelType
from fast_backend_builder.attach.gql_controller import AttachmentBaseController
from fast_backend_builder.utils.helpers.log_activity import log_user_activity
from fast_backend_builder.workflow.gql_controller import TransitionBaseController
from fast_backend_builder.utils.error_logging import log_exception
from tortoise.expressions import Q

CreateSchema = TypeVar("CreateSchema")
UpdateSchema = TypeVar("UpdateSchema")
ResponseSchema = TypeVar("ResponseSchema")
TZ = pytz.timezone("Africa/Dar_es_Salaam")  # or datetime.timezone.utc

class GQLBaseCRUD(AttachmentBaseController[ModelType], TransitionBaseController[ModelType],
                  Generic[ModelType, CreateSchema, UpdateSchema]):
    """
    Base class for all CRUD operations using Tortoise ORM.
    """

    api_type: APIType

    def __init__(self, model: Type[ModelType], response_schema: Optional[Type[ResponseSchema]] = None, api_type: APIType = APIType.GRAPHQL):
        self.model = model
        self.response_schema = response_schema
        self.api_type = api_type
        super().__init__(model)

    async def create(self, obj_in: CreateSchema,
                     condition_function: Optional[Callable[[Dict[str, Any]], Awaitable[ApiResponse]]] = None,
                     post_create_function: Optional[Callable[[ModelType, Dict[str, Any]], Awaitable[None]]] = None
                     ) -> ApiResponse:
        """
        Create an item with optional condition and post-create functions.
        """
        try:

            current_user = Auth.user()
            user_id = current_user.get('user_id')
            username = current_user.get('username')

            data = obj_in.__dict__
            # according shija ntula we comment here waiting front end to  bring enum
            # for key, value in data.items():
            #     if isinstance(value, Enum):
            #         data[key] = value.value

            # Run the condition function if provided and it's async
            if condition_function:
                if inspect.iscoroutinefunction(condition_function):
                    result = await condition_function(data)
                else:
                    result = condition_function(data)

                if isinstance(result, ApiResponse):
                    return result
                else:
                    data = result  # Modified data

            # Remove '_removed_fields' if it exists in data
            removed_fields = data.pop('_removed_fields', {})

            # Create the main object
            # Add created_by_id
            if user_id:
                data['created_by_id'] = user_id
            created_object = await self.model.create(**data)

            await log_user_activity(user_id=user_id, username=username, entity=self.model.Meta.verbose_name,
                                    action='ADDITION',
                                    details=f"Added {self.model.Meta.verbose_name}")
            # Run the post-update function if provided and it's async
            if post_create_function:
                if inspect.iscoroutinefunction(post_create_function):
                    post_result = await post_create_function(created_object, removed_fields)
                else:
                    post_result = post_create_function(created_object, removed_fields)

                if isinstance(post_result, ApiResponse):
                    return post_result

            return ApiResponse(
                status=True,
                code=ResponseCode.SUCCESS,
                message=f"{self.model.Meta.verbose_name} created successfully",
                data=created_object if created_object else None
            )
        except ValueError as ve:
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=str(ve),
                data=None
            )
        except IntegrityError as e:
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=self.parse_integrity_error(e),
                data=None
            )
        except ValidationError as e:
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=str(e),
                data=None
            )
        except Exception as e:
            log_exception(e)
            return ApiResponse(
                status=False,
                code=ResponseCode.FAILURE,
                message=f"Failed to create {self.model.Meta.verbose_name}. Try again.",
                data=None
            )

    async def create_multiple(self, objs_in: List[CreateSchema],
                              condition_function: Optional[Callable[[Dict[str, Any]], Awaitable[ApiResponse]]] = None,
                              post_create_function: Optional[
                                  Callable[[ModelType, Dict[str, Any]], Awaitable[None]]] = None
                              ) -> ApiResponse:
        """
        Create an item with optional condition and post-create functions.
        """
        try:
            created_objects = []

            current_user = Auth.user()
            user_id = current_user.get('user_id')
            username = current_user.get('username')

            for obj_in in objs_in:
                data = obj_in.__dict__
                for key, value in data.items():
                    if isinstance(value, Enum):
                        data[key] = value.value

                    # Run the condition function if provided and it's async
                    if condition_function:
                        if inspect.iscoroutinefunction(condition_function):
                            result = await condition_function(data)
                        else:
                            result = condition_function(data)

                        if isinstance(result, ApiResponse):
                            return result
                        else:
                            data = result  # Modified data

                # Remove '_removed_fields' if it exists in data
                removed_fields = data.pop('_removed_fields', {})

                # Create the main object
                # Add created_by_id
                if user_id:
                    data['created_by_id'] = user_id
                created_object = await self.model.create(**data)
                created_objects.append(created_object)

            await log_user_activity(user_id=user_id, username=username, entity=self.model.Meta.verbose_name,
                                    action='ADDITION',
                                    details=f"Bulk Added {self.model.Meta.verbose_name} ")

            # Run the post-update function if provided and it's async
            if post_create_function:
                if inspect.iscoroutinefunction(post_create_function):
                    await post_create_function(created_objects, removed_fields)
                else:
                    post_create_function(created_objects, removed_fields)

            return ApiResponse(
                status=True,
                code=ResponseCode.SUCCESS,
                message=f"{self.model.Meta.verbose_name} created successfully",
                data=created_objects
            )
        except ValueError as ve:
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=str(ve),
                data=False
            )
        except IntegrityError as e:
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=self.parse_integrity_error(e),
                data=False
            )
        except ValidationError as e:
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=str(e),
                data=False
            )
        except Exception as e:
            log_exception(e)
            return ApiResponse(
                status=False,
                code=ResponseCode.FAILURE,
                message=f"Failed to create {self.model.Meta.verbose_name}. Try again.",
                data=False
            )

    async def update(self, obj_in: UpdateSchema,
                     condition_function: Optional[Callable[[Dict[str, Any]], Awaitable[ApiResponse]]] = None,
                     post_update_function: Optional[Callable[[ModelType, Dict[str, Any]], Awaitable[None]]] = None
                     ) -> ApiResponse:
        """
        Update an item by id.
        """
        obj_data = obj_in.__dict__
        for key, value in obj_data.items():
            if isinstance(value, Enum):
                obj_data[key] = value.value
        try:

            current_user = Auth.user()
            user_id = current_user.get('user_id')
            username = current_user.get('username')

            obj = await self.model.get(id=obj_data.get('id'))

            # Run the condition function if provided and it's async
            if condition_function:
                if inspect.iscoroutinefunction(condition_function):
                    result = await condition_function(obj_data)
                else:
                    result = condition_function(obj_data)

                if isinstance(result, ApiResponse):
                    return result
                else:
                    obj_data = result  # Modified data

            # Remove '_removed_fields' if it exists in data
            removed_fields = obj_data.pop('_removed_fields', {})

            # Update the object
            obj_data.pop("id")
            for key, value in obj_data.items():
                setattr(obj, key, value)
            await obj.save()

            await log_user_activity(user_id=user_id, username=username, entity=self.model.Meta.verbose_name,
                                    action='CHANGE',
                                    details=f"Updated {self.model.Meta.verbose_name}")

            # Run the post-update function if provided and it's async
            if post_update_function:
                if inspect.iscoroutinefunction(post_update_function):
                    post_result = await post_update_function(obj, removed_fields)
                else:
                    post_result = post_update_function(obj, removed_fields)

                if isinstance(post_result, ApiResponse):
                    return post_result

            return ApiResponse(
                status=True,
                code=ResponseCode.SUCCESS,
                message=f"{self.model.Meta.verbose_name} updated successfully",
                data=obj
            )
        except DoesNotExist:
            return ApiResponse(
                status=False,
                code=ResponseCode.NO_RECORD_FOUND,
                message=f"{self.model.Meta.verbose_name} does not exist",
                data=None
            )
        except IntegrityError as e:
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=self.parse_integrity_error(e),
                data=None
            )
        except ValueError as ve:
            log_exception(Exception(ve))
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=str(ve),
                data=None
            )
        except ValidationError as e:
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=str(e),
                data=None
            )
        except Exception as e:
            log_exception(e)
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=f"Failed to update {self.model.Meta.verbose_name}. Try again",
                data=None
            )

    async def get(self, id, fields) -> ApiResponse:
        """
        Get a single item by id.
        """
        related_fields_to_prefetch, modified_fields = self.get_related_field_and_retrieve_fields(fields)

        try:

            # obj = await self.model.filter(id__isnull=False).only(*fields).get(id=id)
            obj = await self.model.filter(id__isnull=False).prefetch_related(*related_fields_to_prefetch).only(
                *modified_fields).get(id=id)

            if self.response_schema:
                data = jsonable_encoder(self.response_schema.model_validate(obj, from_attributes=True))
            else:
                data = obj

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
                data=None
            )
        except Exception as e:
            log_exception(e)
            return ApiResponse(
                status=False,
                code=ResponseCode.FAILURE,
                message=f"Failed to retrieve {self.model.Meta.verbose_name}",
                data=None
            )

    async def get_multiple(self, pagination_params: PaginationParams, fields) -> ApiResponse:
        try:
            query = await self.get_initial_queryset(fields)  # Get the initial query
            query = self.apply_search_filters(query, pagination_params)  # No await
            query = self.apply_filters(query, pagination_params)  # No await
            query = self.apply_sorting(query, pagination_params)  # No await
            query = self.apply_grouping(query, pagination_params)  # No await

            data, count = await self.paginate_data(query, pagination_params)  # Execute query here
            return await self.get_final_queryset(data, count, fields)
        except FieldError as e:
            return self.handle_error(e)
        except Exception as e:
            return self.handle_error(e)

    def get_related_field_and_retrieve_fields(self, fields):
        modified_fields = fields.copy()

        # Initialize an empty list to hold the related fields to prefetch
        related_fields_to_prefetch = []
        for field in fields:
            if field not in self.model._meta.fields_map.items():
                modified_fields.remove(field)

        # Iterate over the model's fields to find related fields
        for field_name, field in self.model._meta.fields_map.items():
            # Check if the field is a foreign key
            # print('field',field.relation)
            # if hasattr(field, 'relation') and field.relation:
            if field_name in fields and isinstance(field, (ForeignKeyFieldInstance, ManyToManyFieldInstance)):

                # Get the related field name
                related_field_name = field_name  # This is the foreign key field
                related_fields_to_prefetch.append(related_field_name)

                # Check if the related field is requested in the fields list
                if related_field_name in modified_fields:
                    # Remove the related field and append its foreign key
                    modified_fields.remove(related_field_name)
                    modified_fields.append(f"{related_field_name}_id")  # Append the foreign key
        return related_fields_to_prefetch, modified_fields

    async def get_initial_queryset(self, fields: List[str]) -> QuerySet[ModelType]:
        # Create a copy of the fields list to avoid modifying the original
        related_fields_to_prefetch, modified_fields = self.get_related_field_and_retrieve_fields(fields)

        # Prefetch related fields dynamically
        query = await self.model.with_headship()

        return query.filter(id__isnull=False).prefetch_related(*related_fields_to_prefetch).only(*modified_fields)

    def apply_search_filters(
            self, query: QuerySet[ModelType], pagination_params: PaginationParams
    ) -> QuerySet[ModelType]:
        if pagination_params.search and pagination_params.search.query:
            search_filters = Q()
            for column in pagination_params.search.columns:
                # Split the column path (e.g., "registration_company__name")
                field_parts = column.split("__")
                # Check if the base field exists in the model
                base_field = field_parts[0]
                if base_field in self.model._meta.fields_map:
                    # Validate nested fields if it's a related field
                    if isinstance(self.model._meta.fields_map[base_field], dict):
                        related_model = self.model._meta.fields_map[base_field]["model_class"]
                        valid = True
                        # Traverse the related field chain
                        for related_field in field_parts[1:]:
                            if related_field not in related_model._meta.fields_map:
                                valid = False
                                break
                            related_model = related_model._meta.fields_map[related_field].get(
                                "model_class", None
                            )
                        if not valid:
                            continue
                    # If valid, construct the filter
                    search_filters |= Q(**{f"{column}__icontains": pagination_params.search.query})
            query = query.filter(search_filters)  # No await
        return query

    def apply_filters(
            self,
            query: QuerySet[ModelType],
            pagination_params: PaginationParams
    ) -> QuerySet[ModelType]:

        if not pagination_params.filters:
            return query

        and_q = Q()
        or_q = Q()
        or_count = 0

        for filter in pagination_params.filters:
            # -------------------------
            # Detect logic
            # -------------------------
            raw_field = filter.field.strip()
            logic = "and"

            if raw_field.startswith("or:"):
                logic = "or"
                raw_field = raw_field[3:]

            field = raw_field
            value = filter.value
            comparator = filter.comparator

            # -------------------------
            # Validate field
            # -------------------------
            base_field = field.split("__")[0]
            field_object = self.model._meta.fields_map.get(base_field)
            if not field_object:
                raise ValueError(f"Invalid filter field: {base_field}")

            # -------------------------
            # Helpers
            # -------------------------
            def parse_list(val):
                if isinstance(val, str):
                    val = val.strip().strip('"').replace('\\"', '"')
                    try:
                        parsed = json.loads(val)
                        if not isinstance(parsed, (list, tuple)):
                            raise ValueError
                        return parsed
                    except Exception:
                        return [v.strip() for v in val.split(",") if v.strip()]
                return val

            # -------------------------
            # Build Q
            # -------------------------
            q = None

            if comparator == "exclude":
                q = ~Q(**{field: value})

            elif comparator == "exact":
                q = Q(**{field: value})

            elif comparator == "isnull":
                q = Q(**{f"{field}__isnull": str(value).lower() == "true"})

            elif comparator == "ne":
                q = ~Q(**{field: value})

            elif comparator in ["icontains", "startswith", "endswith", "contains",
                                "gte", "lte", "gt", "lt"]:

                if comparator in ["gte", "lte", "gt", "lt"]:
                    import datetime
                    if isinstance(field_object, fields.DateField):
                        value = datetime.date.fromisoformat(value)
                    elif isinstance(field_object, fields.DatetimeField):
                        value = datetime.datetime.fromisoformat(value)

                q = Q(**{f"{field}__{comparator}": value})

            elif comparator == "bool":
                q = Q(**{field: str(value).lower() in ("true", "1", "yes")})

            elif comparator == "date":
                from datetime import datetime
                q = Q(**{field: datetime.fromisoformat(value).date()})

            elif comparator in ["in", "nin"]:
                parsed = parse_list(value)
                q = Q(**{f"{field}__in": parsed})
                if comparator == "nin":
                    q = ~q

            else:
                raise ValueError(f"Unsupported filter comparator: {comparator}")

            # -------------------------
            # Combine logically
            # -------------------------
            if logic == "or":
                or_q |= q
                or_count += 1
            else:
                and_q &= q

        # -------------------------
        # Apply once
        # -------------------------
        if or_count:
            return query.filter(and_q & or_q)

        return query.filter(and_q)

    def apply_sorting(self, query: QuerySet[ModelType], pagination_params: PaginationParams) -> QuerySet[ModelType]:
        sort_by = pagination_params.sortBy
        sort_order = pagination_params.sortOrder
        model_fields = self.model._meta.fields_map

        if sort_by:
            # Split the sort_by field to handle related fields
            field_parts = sort_by.split("__")
            base_field = field_parts[0]

            # Validate base field
            if base_field in model_fields:
                is_valid = True
                related_model = None

                # Traverse related fields, if applicable
                if isinstance(model_fields[base_field], dict):
                    related_model = model_fields[base_field]["model_class"]
                    for related_field in field_parts[1:]:
                        if related_field not in related_model._meta.fields_map:
                            is_valid = False
                            break
                        related_model = related_model._meta.fields_map[related_field].get("model_class", None)

                if is_valid:
                    order = "" if sort_order == "asc" else "-"
                    query = query.order_by(f"{order}{sort_by}")

        # Default sorting if no valid sort_by is provided
        # query = query.order_by("-id")

        return query

    def apply_grouping(self, query: QuerySet[ModelType], pagination_params: PaginationParams) -> QuerySet[ModelType]:
        """Applies grouping and aggregation to the query, including CONCAT and GROUP_CONCAT."""
        groups = pagination_params.groupBy
        group_functions = pagination_params.groupFunctions

        if groups:
            for group in groups:
                field = group.field
                format = group.format

                if format:
                    # Handle date/datetime formats
                    if format.startswith("range__"):
                        range_type = format.split("__")[1]
                        if range_type in {"weekly", "monthly", "quarterly", "yearly"}:
                            query = self.group_by_date(query, field, range_type)
                        else:
                            raise ValueError(f"Invalid date range format: {format}")

                    # Handle number scaling/ranges
                    elif format.startswith("scale__"):
                        scale_factor = float(format.split("__")[1])
                        query = self.group_by_scaled_numbers(query, field, scale_factor)

                    elif format.startswith("range__"):
                        range_step = int(format.split("__")[1])
                        query = self.group_by_number_range(query, field, range_step)

                    # Handle strings
                    elif format == "starts_with":
                        query = query.annotate(
                            grouped_field=FExpression(f"LEFT({field}, 1)")
                        ).group_by("grouped_field")

                    elif format.startswith("length__"):
                        length = int(format.split("__")[1])
                        query = query.annotate(
                            grouped_field=FExpression(f"LENGTH({field})")
                        ).filter(Q(grouped_field=length))

                else:
                    # Simple grouping by field
                    query = query.group_by(field).all()

        # Apply aggregation functions
        if group_functions:
            for group_function in group_functions:
                field = group_function.field
                function_name = group_function.function

                # Use FunctionMapper to retrieve the appropriate function
                function = self.get_function(function_name)

                query = query.annotate(**{f"{field}_{function_name}": function(field)})

        return query

    def group_by_date(self, query: QuerySet, field: str, range_type: str) -> QuerySet:
        """Groups by date range (weekly, monthly, quarterly, yearly)."""
        if range_type == "weekly":
            query = query.annotate(grouped_field=FExpression(f"DATE_TRUNC('week', {field})"))
        elif range_type == "monthly":
            query = query.annotate(grouped_field=FExpression(f"DATE_TRUNC('month', {field})"))
        elif range_type == "quarterly":
            query = query.annotate(grouped_field=FExpression(f"DATE_TRUNC('quarter', {field})"))
        elif range_type == "yearly":
            query = query.annotate(grouped_field=FExpression(f"DATE_TRUNC('year', {field})"))
        return query.group_by("grouped_field")

    def group_by_scaled_numbers(self, query: QuerySet, field: str, scale_factor: float) -> QuerySet:
        """Groups numbers by scaling with a factor."""
        query = query.annotate(
            grouped_field=FExpression(f"FLOOR({field} / {scale_factor}) * {scale_factor}")
        )
        return query.group_by("grouped_field")

    def group_by_number_range(self, query: QuerySet, field: str, range_step: int) -> QuerySet:
        """Groups numbers by specified range step."""
        query = query.annotate(
            grouped_field=FExpression(f"FLOOR({field} / {range_step}) * {range_step}")
        )
        return query.group_by("grouped_field")

    def get_function(self, name: str) -> Function:
        """Retrieve the appropriate function based on the name."""
        function_map = {
            "sum": Sum,
            "count": Count,
            "avg": Avg,
            "min": Min,
            "max": Max,
            "concat": Concat,  # Built-in concatenation function
        }
        if name not in function_map:
            raise ValueError(f"Unsupported function: {name}")
        return function_map[name]

    async def paginate_data(self, query: QuerySet[ModelType], pagination_params: PaginationParams) -> Tuple:
        offset = (pagination_params.page - 1) * pagination_params.pageSize
        limit = pagination_params.pageSize
        return await query.offset(offset).limit(limit).all(), await query.count()

    async def get_final_queryset(self, data, paginator_count, fields: Optional[List[str]] = []) -> ApiResponse:
        # Check if a custom response schema is provided
        if self.response_schema:
            data = [
                jsonable_encoder(
                    self.response_schema.model_validate(obj, from_attributes=True)
                )
                for obj in data
            ]
        return ApiResponse(
            status=True,
            code=ResponseCode.SUCCESS,
            message=f"{self.model.Meta.verbose_name_plural} fetched successfully",
            data=PaginatedResponse(
                items=data,
                item_count=paginator_count,
            )
        )

    async def delete(self, id) -> ApiResponse:
        """
        Delete an item by id.
        """
        try:

            current_user = Auth.user()
            user_id = current_user.get('user_id')
            username = current_user.get('username')

            obj = await self.model.get(id=id)
            obj_dict = obj.__dict__
            # Preprocess obj_dict to convert datetime objects to strings
            for key, value in obj_dict.items():
                if isinstance(value, (datetime, date)):
                    obj_dict[key] = value.isoformat()  # Convert to ISO 8601 string
                elif isinstance(value, UUID):  # Handle UUID
                    obj_dict[key] = str(value)  # Convert to string

            await obj.delete()
            await log_user_activity(user_id=user_id, username=username, entity=self.model.Meta.verbose_name,
                                    action='DELETE',
                                    details=f"Deleted {self.model.Meta.verbose_name}")
            return ApiResponse(
                status=True,
                code=ResponseCode.SUCCESS,
                message=f"{self.model.Meta.verbose_name} deleted successfully",
                data=None
            )
        except DoesNotExist:
            return ApiResponse(
                status=False,
                code=ResponseCode.NO_RECORD_FOUND,
                message=f"{self.model.Meta.verbose_name} does not exist",
                data=None
            )
        except Exception as e:
            log_exception(e)
            return ApiResponse(
                status=False,
                code=ResponseCode.FAILURE,
                message=f"Failed to Delete Data. Try Again",
                data=None
            )

    def handle_error(self, e: Exception) -> ApiResponse:
        log_exception(e)
        return ApiResponse(
            status=False,
            code=ResponseCode.FAILURE,
            message=f"Error Retrieving Data. Try Again",
            data=None
        )

    def parse_integrity_error(self, e: IntegrityError) -> str:
        error_message = str(e).lower()  # normalize

        if "unique" in error_message:
            return f"A {self.model.Meta.verbose_name} with the same details already exists."

        if "foreign key" in error_message:
            return f"The specified related record does not exist."

        if "not null" in error_message:
            return f"One or more required fields cannot be null."

        if "check constraint" in error_message:
            return f"The provided data does not meet validation requirements."

        log_exception(e)

        # default / unknown constraint
        return "An unexpected database error occurred."
