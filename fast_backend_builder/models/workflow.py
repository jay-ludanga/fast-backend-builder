from datetime import timedelta, datetime

from tortoise import fields

from tortoise.functions import Max  # Import Max function

from fast_backend_builder.models import TimeStampedModel
from fast_backend_builder.notifications.service import NotificationService
from fast_backend_builder.workflow.exceptions import NoCurrentStepError, MissingStepError, PermissionDeniedError, \
    MissingRemarkError, WorkflowException

'''List of Models'''

User = "models.User"  # lazy reference


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

    async def get_initial_step(self):
        # Get the WorkflowStep with the smallest order in this workflow
        initial_step = await WorkflowStep.filter(workflow=self).order_by('order').first()
        if initial_step.code != 'DRAFT':
            raise WorkflowException("First Workflow Step code must be DRAFT")
        return initial_step

    async def get_final_step(self):
        # Get the WorkflowStep with the largest order in this workflow
        final_step = await WorkflowStep.filter(workflow=self).order_by('-order').first()
        return final_step

    async def can_transit(self, current_step: 'WorkflowStep', next_step_obj: 'WorkflowStep', user: User,
                          remarks) -> bool:
        # Get the transition that is allowed from this step to the next step
        transition = await Transition.filter(from_step=current_step, to_step=next_step_obj).prefetch_related(
            'groups').first()

        if not transition:
            return False  # No transition found

        if transition.require_remark and not remarks:
            return False  # Transition requires a remark but none was provided

        # Optimize group retrieval using a single query with set comparison for user groups
        user_groups = await user.groups.all().values_list('id', flat=True)
        allowed_groups = set(group.id for group in transition.groups)

        # Check if there's any overlap between the user's groups and allowed groups
        return bool(set(user_groups) & allowed_groups) or user.is_superuser

    async def transit(self, object_id: str, next_step: str, user_id: str, connection, remark: str = None):
        """
        @param object_id: Object Model ID
        @param next_step: Next Step Code
        @param user_id: User ID
        @param connection: Db Transaction connection
        @param remark: Remark if Any
        """
        try:
            # Get the current step from the last evaluation
            last_evaluation = await Evaluation.filter(object_id=object_id, object_name=self.code).prefetch_related(
                'workflow_step'  # Correct singular field
            ).order_by('-created_at').first()

            if not last_evaluation:
                current_step = await self.get_initial_step()
            else:
                current_step = last_evaluation.workflow_step

            # Get the next step using the provided code
            next_step_obj = await WorkflowStep.get_or_none(code=next_step, workflow=self)
            if not next_step_obj:
                raise MissingStepError(next_step_obj)

            # Check if the user exists and optimize user import
            user = await User.get_or_none(id=user_id)
            if not user:
                raise WorkflowException(f"User does not exist.")

            # Check if the user is allowed to transition
            if not await self.can_transit(current_step, next_step_obj, user, remark):
                raise PermissionDeniedError(user, current_step, next_step_obj)

            # Transition requires a remark, ensure it's present
            transition = await Transition.filter(from_step=current_step, to_step=next_step_obj).first()
            if transition and transition.require_remark and not remark:
                raise MissingRemarkError()

            # Create a new Evaluation recording the transition
            new_evaluation = await Evaluation.create(
                object_name=self.code,
                object_id=object_id,
                workflow_step=next_step_obj,
                remark=remark,
                user=user,
                using_db=connection
            )

            await new_evaluation.notify()

            return new_evaluation
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

    async def notify(self):
        notification_content = self.workflow_step.notification_content_type
        message = {
            "job_name": f"{self.object_name} Workflow Notification",
            "channel_type": self.workflow_step.workflow.notification_channel,
            "recipient": None,
            "content_type": notification_content,
            "args": {
                "client_name": None,
                "actor_name": None
            }
        }

        """ Send a notification if the workflow step requires it. """
        if self.workflow_step.notify_applicant:
            # Implement the logic to send an email or other form of notification
            first_evaluation = await Evaluation.filter(object_id=self.object_id,
                                                       object_name=self.object_name).select_related('user').order_by(
                'created_at').first()

            if first_evaluation:
                message[
                    "recipient"] = first_evaluation.user.email  # Assuming you have a list of recipients in the messagefirst_evaluation.user.email
                message["args"]["actor_name"] = "ARMS Team"
                message["args"]["client_name"] = first_evaluation.user.get_short_name()

                # Now you can pass the message to your notification sending logic, e.g.:
                notification = NotificationService.get_instance()
                await notification.put_message_on_queue('Notifications', message)

        if self.workflow_step.notify_evaluator:
            # Fetch the next transition with prefetching of related groups and users
            next_transition = await Transition.filter(from_step=self.workflow_step, direction='FORWARD') \
                .prefetch_related('groups__users') \
                .order_by('id') \
                .first()

            if next_transition:
                # Collect all the users from the groups linked to this transition asynchronously
                users = set()

                # Asynchronously iterate through the groups
                groups = await next_transition.groups.all()

                for group in groups:
                    group_users = await group.users.all()  # Fetch users for each group asynchronously
                    users.update(group_users)

                # Now you have the set of users, proceed with your notification logic
                recipient_users = [(user.id, user.email, user.get_short_name()) for user in users]
                for user_id, email, short_name in recipient_users:
                    message["recipient"] = email
                    message["args"]["actor_name"] = "ARMS Team"
                    message["content_type"] = notification_content
                    message["args"]["client_name"] = short_name  # Personalize message with the user's short name
                    # Pass the message to your notification sending logic
                    notification = NotificationService.get_instance()
                    await notification.put_message_on_queue('Notifications', message)
