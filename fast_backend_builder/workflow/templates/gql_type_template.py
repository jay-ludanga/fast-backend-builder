import strawberry

from fast_backend_builder.workflow.response import EvaluationStatusResponse

'''EVALUATION_RESPONSE'''
@strawberry.type
class _MODEL_EvaluationStatusResponse(EvaluationStatusResponse):
    pass