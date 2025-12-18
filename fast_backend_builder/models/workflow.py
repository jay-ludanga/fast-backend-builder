from datetime import timedelta, datetime

from tortoise import fields

from tortoise.functions import Max  # Import Max function

from fast_backend_builder.models import TimeStampedModel
from fast_backend_builder.notifications.service import NotificationService
from fast_backend_builder.utils.enums import NotificationChannel
from fast_backend_builder.utils.str_helpers import normalize_model_name
from fast_backend_builder.workflow.exceptions import NoCurrentStepError, MissingStepError, PermissionDeniedError, \
    MissingRemarkError, WorkflowException

'''List of Models'''


class Workflow(TimeStampedModel):
    name = fields.CharField(max_length=255, unique=True)
    code = fields.CharField(max_length=100, unique=True)
    description = fields.TextField(null=True)
    notification_channel = fields.JSONField(default=list)  # stores ["SMS", "Email"]
    is_active = fields.BooleanField(default=True)  # Represents if it's Active or not

    steps: fields.ReverseRelation["WorkflowStep"]

    created_by = fields.ForeignKeyField(
        'models.User',
        null=True,
        on_delete=fields.SET_NULL,
        related_name="workflows_created"  # Specific related_name to avoid conflict
    )

    class Meta:
        table = "workflows"  # Specify the database table name
        verbose_name = "Workflow"  # Human-readable name for admin, etc.
        verbose_name_plural = "Workflows"  # Plural version of the model name

    async def get_initial_step(self, connection):
        step = await WorkflowStep.filter(
            workflow=self,
        ).using_db(connection).order_by('order').first()

        if not step or step.code != 'DRAFT':
            raise WorkflowException("First Workflow Step code must be DRAFT")

        return step

    async def get_final_step(self):
        # Get the WorkflowStep with the largest order in this workflow
        final_step = await WorkflowStep.filter(workflow=self).order_by('-order').first()
        return final_step

    async def can_transit(
            self,
            current_step,
            next_step,
            user,
            remark,
            connection,
    ) -> bool:
        transition = await Transition.filter(
            from_step=current_step,
            to_step=next_step,
        ).using_db(connection).prefetch_related('groups').first()

        if not transition:
            return False

        if transition.require_remark and not remark:
            raise MissingRemarkError()

        user_group_ids = await user.groups.all().using_db(connection).values_list('id', flat=True)
        allowed_group_ids = {g.id for g in transition.groups}

        return bool(set(user_group_ids) & allowed_group_ids) or user.is_superuser

    async def transit(self, object_id: str, next_step: str, user_id: str, connection, remark: str = None):
        """
        @param object_id: Object Model ID
        @param next_step: Next Step Code
        @param user_id: User ID
        @param connection: Db Transaction connection
        @param remark: Remark if Any
        """
        try:
            last_evaluation = await Evaluation.filter(
                object_id=object_id,
                object_name=self.code,
            ).using_db(connection).prefetch_related(
                'workflow_step'
            ).order_by('-created_at').first()

            if last_evaluation:
                current_step = last_evaluation.workflow_step
            else:
                current_step = await self.get_initial_step(connection)

            next_step_obj = await WorkflowStep.filter(
                code=next_step,
                workflow=self,
            ).using_db(connection).first()

            if not next_step_obj:
                raise MissingStepError(next_step)

            from fast_backend_builder.utils.config import get_user_model
            User = get_user_model()

            user = await User.filter(id=user_id).using_db(connection).first()
            if not user:
                raise WorkflowException("User does not exist")

            if not await self.can_transit(
                    current_step,
                    next_step_obj,
                    user,
                    remark,
                    connection,
            ):
                raise PermissionDeniedError(user, current_step, next_step_obj)

            evaluation = await Evaluation.create(
                object_name=self.code,
                object_id=object_id,
                workflow_step=next_step_obj,
                remark=remark,
                user=user,
                using_db=connection,
            )

            return evaluation, next_step_obj.code

        except WorkflowException as we:
            raise WorkflowException(we)
        except Exception as e:
            raise WorkflowException(f"Failed to transit {next_step} step")


class WorkflowStep(TimeStampedModel):
    name = fields.CharField(max_length=255)
    code = fields.CharField(max_length=100)
    notify_applicant = fields.BooleanField(default=False)
    notify_evaluator = fields.BooleanField(default=False)
    notification_content_type = fields.CharField(max_length=100, null=True)
    is_time_constrained = fields.BooleanField(default=False)
    due_days = fields.IntField(default=0)
    workflow = fields.ForeignKeyField('models.Workflow', related_name='steps', on_delete=fields.RESTRICT)
    order = fields.IntField(default=0)  # Added order field with default value 0

    created_by = fields.ForeignKeyField(
        'models.User',
        null=True,
        on_delete=fields.SET_NULL,
        related_name="workflow_steps_created"  # Specific related_name to avoid conflict
    )

    class Meta:
        table = "workflow_steps"  # Specify the database table name
        verbose_name = "Workflow Step"  # Human-readable name for admin, etc.
        verbose_name_plural = "Workflow Steps"  # Plural version of the model name
        unique_together = (('code', 'workflow'),)

    def __str__(self):
        return self.name

    async def save(self, *args, **kwargs):
        if not self.order:  # Only set the order if it's not manually provided
            max_order = await self.get_max_order_for_workflow() or 0
            self.order = max_order + 10
        await super().save(*args, **kwargs)

        # Async method to get the maximum order for the workflow

    async def get_max_order_for_workflow(self):
        # Filter for non-null 'order' values and calculate the maximum order
        max_order = await WorkflowStep.filter(workflow_id=self.workflow_id).exclude(order__isnull=True).annotate(
            max_order=Max('order')).values('max_order')

        # Return the maximum order, or 0 if no valid records are found
        return max_order[0]['max_order'] if max_order and max_order[0]['max_order'] is not None else 0

    async def is_inuse(self) -> bool:
        return await Evaluation.filter(workflow_step=self).exists()


class Transition(TimeStampedModel):
    from_step = fields.ForeignKeyField('models.WorkflowStep', related_name='transitions_from',
                                       on_delete=fields.RESTRICT)
    to_step = fields.ForeignKeyField('models.WorkflowStep', related_name='transitions_to', on_delete=fields.RESTRICT)

    # Many-to-Many with explicit through table
    groups = fields.ManyToManyField('models.Group', related_name='transitions')
    require_remark = fields.BooleanField(default=False)
    condition_description = fields.TextField(null=True)
    direction = fields.CharField(default='FORWARD', max_length=100)
    action_text = fields.CharField(max_length=100, null=True)

    created_by = fields.ForeignKeyField(
        'models.User',
        null=True,
        on_delete=fields.SET_NULL,
        related_name="transitions_created"  # Specific related_name to avoid conflict
    )

    class Meta:
        table = "transitions"
        verbose_name = "Transition"
        verbose_name_plural = "Transitions"

    @classmethod
    async def get_next_transition(cls, current_step, direction='FORWARD'):
        """
        Get the next transition based on the current step and direction.

        :param current_step: The current workflow step (WorkflowStep object)
        :param direction: The direction of the transition (default is 'FORWARD')
        :return: The next Transition object or None if no transition is found
        """
        # Query for the next transition where the current step is the `from_step` and the direction matches
        next_transition = await cls.filter(
            from_step=current_step,
            direction=direction
        ).first()

        return next_transition


# Evaluation Status
class Evaluation(TimeStampedModel):
    object_name = fields.CharField(max_length=50)
    object_id = fields.CharField(max_length=50)
    workflow_step = fields.ForeignKeyField('models.WorkflowStep', related_name='evaluations', on_delete=fields.RESTRICT)
    remark = fields.CharField(max_length=200, null=True)
    user = fields.ForeignKeyField(
        'models.User',
        related_name='evaluations',
        on_delete=fields.RESTRICT,
        help_text="User evaluations"
    )

    class Meta:
        table = "evaluations"
        verbose_name = "Evaluation"
        verbose_name_plural = "Evaluations"

    def __str__(self):
        return f"{self.object_name} set to ({self.status} by {self.user.email})"

    async def is_final_stage(self) -> bool:
        """ Check if the current evaluation is at the final stage of the workflow. """
        # Use the method from WorkflowStep to get the max order for the workflow
        max_order = await self.workflow_step.get_max_order_for_workflow()

        # Return True if the current step's order matches the max order
        return self.workflow_step.order == max_order

    async def is_overdue(self) -> bool:
        """ Check if the current evaluation is overdue based on time constraints. """
        if self.workflow_step.is_time_constrained:
            due_date = self.created_at + timedelta(days=self.workflow_step.due_days)
            return datetime.now() > due_date
        return False

    # Helper to collect notifications for a list of users over multiple channels

    async def notify(self):
        notification_content = self.workflow_step.notification_content_type
        # Fetch the workflow object explicitly
        """Send notifications to applicant and evaluators based on workflow step flags."""
        message_template = {
            "job_name": f"{normalize_model_name(self.object_name)} Workflow Notification",
            "notification_channel": None,
            "recipient": None,
            "content_type": notification_content,
            "args": {
                "client_name": None,
                "resource_name": None,
                "step": None,
                "actor_name": "ARMS Team",
            }
        }

        push_message = {
            "job_name": f"{normalize_model_name(self.object_name)} Push Notification",
            "user_id": None,
            "message": None,
            "args": {
                "type": None,
                "type_id": None,
            }

        }

        notification = NotificationService.get_instance()

        # Normalize channels to a list
        workflow_step = await self.workflow_step
        workflow = await workflow_step.workflow
        channels = workflow.notification_channel or []
        if isinstance(channels, str):
            channels = [channels]

        push_message["args"]["type"] = self.object_name
        push_message["args"]["type_id"] = self.object_id

        # Helper to send notifications to a list of users over multiple channels
        async def collect_messages_for_users(users: list, notify: str):
            """Collects notification messages and push messages for users."""
            notification_messages = []
            push_messages = []

            for user in users:
                # 1. Collect general notifications (Email/SMS)
                for channel in channels:
                    # Skip SMS if phone number is missing
                    if channel == NotificationChannel.SMS and not user.phone_number:
                        continue

                    message_copy = message_template.copy()
                    message_copy["args"] = message_template["args"].copy()
                    message_copy["args"]["client_name"] = user.get_short_name()
                    message_copy["args"]["resource_name"] = normalize_model_name(self.object_name)
                    message_copy["args"]["step"] = workflow_step.code

                    if channel == NotificationChannel.EMAIL:
                        message_copy["recipient"] = user.email
                    elif channel == NotificationChannel.SMS:
                        message_copy["recipient"] = user.phone_number

                    message_copy["notification_channel"] = channel
                    notification_messages.append(message_copy)  # Collect instead of putting on queue

                # 2. Collect in-app/push notifications
                current_push_message = push_message.copy()
                current_push_message["user_id"] = str(user.id)
                current_push_message['notification_channel'] = 'PUSH'

                if notify == 'applicant':
                    current_push_message[
                        'message'] = f"Your {normalize_model_name(self.object_name)} has been {workflow_step.code}"
                else:
                    current_push_message['message'] = (
                        f"The new {normalize_model_name(self.object_name)} is ready for your evaluation. "
                        f"Please check it out at your earliest convenience.")

                push_messages.append(current_push_message)  # Collect instead of putting on queue

            return notification_messages, push_messages

        # Notify applicant
        applicant_notification_msgs = []
        applicant_push_msgs = []
        if self.workflow_step.notify_applicant:
            first_evaluation = await Evaluation.filter(
                object_id=self.object_id,
                object_name=self.object_name
            ).select_related('user').order_by('created_at').first()

            if first_evaluation:
                notif_msgs, push_msgs = await collect_messages_for_users([first_evaluation.user], 'applicant')
                applicant_notification_msgs.extend(notif_msgs)
                applicant_push_msgs.extend(push_msgs)

        # Notify evaluators
        evaluator_notification_msgs = []
        evaluator_push_msgs = []
        if self.workflow_step.notify_evaluator:
            next_transition = await Transition.filter(
                from_step=self.workflow_step,
                direction='FORWARD'
            ).prefetch_related('groups__users').order_by('id').first()

            if next_transition:
                users = set()
                for group in await next_transition.groups.all():
                    users.update(await group.users.all())

                notif_msgs, push_msgs = await collect_messages_for_users(list(users), 'evaluator')
                evaluator_notification_msgs.extend(notif_msgs)
                evaluator_push_msgs.extend(push_msgs)

        # 3. Send all collected messages in bulk
        all_notification_messages = applicant_notification_msgs + evaluator_notification_msgs
        all_push_messages = applicant_push_msgs + evaluator_push_msgs

        if all_notification_messages:
            await notification.put_bulk_messages_on_queue('Notifications', all_notification_messages)

        if all_push_messages:
            await notification.put_bulk_messages_on_queue('Notifications', all_push_messages)
