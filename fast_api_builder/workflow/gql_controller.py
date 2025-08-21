import base64
from enum import Enum
from io import BytesIO
import os
from typing import Any, Callable, Dict, Generic, Optional, Type

from pydantic import ValidationError
from strawberry import Info
from tortoise.exceptions import DoesNotExist, IntegrityError
from tortoise.transactions import in_transaction
from decouple import config
from fast_api_builder.attach.request import AttachmentUpload
from fast_api_builder.attach.service import MinioService
from fast_api_builder.auth.auth import Auth
from fast_api_builder.models.workflow import Evaluation, Workflow

from fast_api_builder.utils.error_logging import log_exception


from fast_api_builder.common.response.codes import ResponseCode
from fast_api_builder.common.response.schemas import ApiResponse, PaginatedResponse
from fast_api_builder.common.schemas import ModelType

from fast_api_builder.utils.helpers.log_activity import log_user_activity
from fast_api_builder.workflow.request import EvaluationStatus
from fast_api_builder.workflow.exceptions import WorkflowException
from fast_api_builder.workflow.response import EvaluationStatusResponse


# MinIO setup
class TransitionBaseController(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def after_transit(self, obj: Type[ModelType], evaluation: Evaluation, connection):
        """
        @param: connection: db transaction connection
        """
        pass

    async def transit(self, evaluation_status: EvaluationStatus) -> ApiResponse:
        """
        Creates new transition for ModelType.
        """
        try:
            current_user = Auth.user_data()
            user_id = current_user.get('user_id')
            username = current_user.get('email')

            async with in_transaction() as connection:

                workflow: Workflow = await Workflow.filter(code=self.model.__name__, is_active=True).first()

                if workflow:

                    obj = await self.model.get(id=evaluation_status.object_id)

                    evaluation: Evaluation = await workflow.transit(
                        object_id=evaluation_status.object_id,
                        next_step=evaluation_status.status,
                        remark=evaluation_status.remark,
                        user_id=user_id,
                        connection=connection
                    )

                    obj.evaluation_status = evaluation.workflow_step.code
                    await obj.save(using_db=connection)
                    await self.after_transit(obj, evaluation, connection)

                    await log_user_activity(user_id=user_id, username=username,
                                            entity=Evaluation.Meta.verbose_name,
                                            action='CHANGE',
                                            details=f"{self.model.Meta.verbose_name} transitioned to {evaluation.workflow_step.name} successfully")

                    return ApiResponse(
                        status=True,
                        code=ResponseCode.SUCCESS,
                        message=f"{self.model.Meta.verbose_name} transitioned to {evaluation.workflow_step.name} successfully",
                        data=True
                    )
                else:
                    return ApiResponse(
                        status=False,
                        code=ResponseCode.BAD_REQUEST,
                        message=f"Workflow of {self.model.Meta.verbose_name} is not configured properly",
                        data=False
                    )

        except WorkflowException as ve:
            log_exception(Exception(ve))
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=f"{str(ve)}",
                data=False
            )
        except DoesNotExist:
            return ApiResponse(
                status=False,
                code=ResponseCode.NO_RECORD_FOUND,
                message=f"The {self.model.Meta.verbose_name} does not exist",
                data=False
            )
        except ValueError as ve:
            log_exception(Exception(ve))
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=str(ve),
                data=False
            )
        except IntegrityError as e:
            log_exception(Exception(e))
            # Check the exception message to identify a unique constraint violation

            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=self.parse_integrity_error(e),
                data=False
            )
        except ValidationError as e:
            log_exception("type... ", Exception(type(e)))
            log_exception(e)
            # Check the exception message to identify a unique constraint violation
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
                message=f"Failed to transit {self.model.Meta.verbose_name}. Try again.",
                data=None
            )

    async def get_transitions(self, model_id: int) -> ApiResponse:
        try:
            evaluation_status = await Evaluation.filter(object_id=model_id, object_name=self.model.__name__).select_related('user','workflow_step')
            data_list = [EvaluationStatusResponse(
                id=evaluation.id,
                object_name=evaluation.object_name,
                object_id=evaluation.object_id,
                status=evaluation.workflow_step.code,
                remark=evaluation.remark,
                user_id=evaluation.user.id,
                user_full_name = evaluation.user.get_short_name(),
                created_at=evaluation.created_at

            )for evaluation in evaluation_status]


            return ApiResponse(
                status=True,
                code=ResponseCode.SUCCESS,
                message=f"{self.model.Meta.verbose_name} evaluation statuses fetched successfully",
                data=data_list,

            )
        except Exception as e:
            log_exception(Exception(e))
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,
                message=f"Failed to fetch {self.model.Meta.verbose_name} evaluation statuses. Try again",
                data=None
            )
