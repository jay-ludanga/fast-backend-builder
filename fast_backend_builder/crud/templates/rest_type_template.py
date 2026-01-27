from typing import Optional
from pydantic import BaseModel

'''List of Types'''
class _MODEL_Response(BaseModel):
    id: Optional[str]
    '''FIELDS'''