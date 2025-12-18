from typing import Generic, Type

from tortoise.exceptions import DoesNotExist, IntegrityError, ValidationError
from tortoise.transactions import in_transaction

from fast_backend_builder.auth.auth import Auth
from fast_backend_builder.common.response.codes import ResponseCode
from fast_backend_builder.common.response.schemas import ApiResponse
from fast_backend_builder.common.schemas import ModelType
from fast_backend_builder.models.workflow import Evaluation, Workflow
from fast_backend_builder.utils.error_logging import log_exception
from fast_backend_builder.utils.helpers.log_activity import log_user_activity
from fast_backend_builder.workflow.exceptions import WorkflowException
from fast_backend_builder.workflow.request import EvaluationStatus
from fast_backend_builder.workflow.response import EvaluationStatusResponse


# MinIO setup
class TransitionBaseController(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def before_transit(
            self,
            evaluation_status: EvaluationStatus,
            obj: ModelType,
            connection,
    ):
        pass

    async def after_transit(
            self,
            obj: ModelType,
            evaluation: Evaluation,
            connection,
    ):
        pass

    async def transit(self, evaluation_status: EvaluationStatus) -> ApiResponse:
        current_user = Auth.user()
        user_id = current_user.get("user_id")
        username = current_user.get("username")

        try:
            async with in_transaction("default") as connection:
                obj = await self.model.get(
                    id=evaluation_status.object_id,
                    using_db=connection,
                )

                res = await self.before_transit(evaluation_status, obj, connection)
                if isinstance(res, ApiResponse):
                    raise WorkflowException(res.message)

                workflow = await Workflow.filter(
                    code=self.model.__name__,
                    is_active=True,
                ).using_db(connection).first()

                if not workflow:
                    raise WorkflowException(
                        f"Workflow of {self.model.Meta.verbose_name} is not configured properly"
                    )

                evaluation, next_step_code = await workflow.transit(
                    object_id=evaluation_status.object_id,
                    next_step=evaluation_status.status,
                    user_id=user_id,
                    remark=evaluation_status.remark,
                    connection=connection,
                )

                obj.evaluation_status = next_step_code
                await obj.save(using_db=connection)

                # ⚠️ if this fails → FULL ROLLBACK
                await self.after_transit(obj, evaluation, connection)

            # ✅ COMMIT ONLY HAPPENS HERE

            await log_user_activity(
                user_id=user_id,
                username=username,
                entity=Evaluation.Meta.verbose_name,
                action="CHANGE",
                details=f"{self.model.Meta.verbose_name} transitioned to {next_step_code}",
            )

            return ApiResponse(
                status=True,
                code=ResponseCode.SUCCESS,
                message=f"{self.model.Meta.verbose_name} transitioned successfully",
                data=True,
            )


        except WorkflowException as we:
            log_exception(we)
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,  # custom code for workflow errors
                message=f"Workflow error: {str(we)}",
                data=False,
            )


        except ValueError as ve:
            log_exception(ve)
            return ApiResponse(
                status=False,
                code=ResponseCode.BAD_REQUEST,  # different custom code if you want
                message=f"Value error: {str(ve)}",
                data=False,
            )


        except Exception as e:
            log_exception(e)
            return ApiResponse(
                status=False,
                code=ResponseCode.FAILURE,  # generic failure for anything else
                message=f"Unexpected error while transitioning {self.model.Meta.verbose_name}",
                data=False,
            )

    async def get_transitions(self, model_id: str) -> ApiResponse:
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
