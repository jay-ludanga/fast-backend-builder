from typing import Optional
import strawberry

'''List of Inputs'''
@strawberry.input
class _MODEL_Create:
    '''CREATE'''
    
@strawberry.input
class _MODEL_Update(_MODEL_Create):
    id: str