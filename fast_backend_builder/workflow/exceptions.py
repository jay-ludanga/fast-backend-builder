class WorkflowException(Exception):
    """Base exception class for Workflow errors."""
    pass

class InvalidTransitionError(WorkflowException):
    """Raised when an invalid transition between workflow steps is attempted."""
    def __init__(self, current_step, next_step):
        self.current_step = current_step
        self.next_step = next_step
        super().__init__(f"Invalid transition from '{self.current_step}' to '{self.next_step}'.")

class PermissionDeniedError(WorkflowException):
    """Raised when a user lacks permission to perform a transition."""
    def __init__(self, user, current_step, next_step):
        self.user = user
        self.current_step = current_step
        self.next_step = next_step
        super().__init__(f"User '{self.user.email}' does not have permission to transition from '{self.current_step}' to '{self.next_step}'.")

class MissingStepError(WorkflowException):
    """Raised when a required workflow step is missing."""
    def __init__(self, step_code):
        self.step_code = step_code
        super().__init__(f"Supplied Workflow step with code not found.")

class MissingRemarkError(WorkflowException):
    """Raised when a remark is required but not provided."""
    def __init__(self):
        super().__init__("A remark is required for this transition but none was provided.")

class NoCurrentStepError(WorkflowException):
    """Raised when the current step cannot be determined."""
    def __init__(self, object_id, object_name):
        self.object_id = object_id
        self.object_name = object_name
        super().__init__(f"No current step found for object '{self.object_name}' with ID '{self.object_id}'.")

class WorkflowStepOrderError(WorkflowException):
    """Raised when there's an error in setting the workflow step order."""
    def __init__(self, workflow_id):
        self.workflow_id = workflow_id
        super().__init__(f"Unable to determine the order for workflow '{self.workflow_id}'.")

class EvaluationError(WorkflowException):
    """Raised for errors in creating or processing evaluations."""
    def __init__(self, message="An error occurred while processing the evaluation."):
        super().__init__(message)
