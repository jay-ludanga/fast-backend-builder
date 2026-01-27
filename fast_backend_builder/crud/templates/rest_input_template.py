from typing import Optional
from pydantic import BaseModel

'''List of Inputs'''
class _MODEL_Create(BaseModel):
    '''CREATE'''
    
class _MODEL_Update(_MODEL_Create):
    id: str