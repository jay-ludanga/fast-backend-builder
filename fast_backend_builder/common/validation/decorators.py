import inspect
from functools import wraps, partial
from typing import List, Type, Union

from fast_backend_builder.common.response.codes import ResponseCode
from fast_backend_builder.common.response.schemas import ApiResponse
from fast_backend_builder.common.validation.field_validator import FieldValidator, ValidationError

def model_validator(func):
    func._decorator_name_ = 'model_validator'
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        return await func(self, *args, **kwargs)
    return wrapper

def model_formater(func):
    func._decorator_name_ = 'model_formater'
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        return await func(self, *args, **kwargs)
    return wrapper

def validation_rules(func):
    func._decorator_name_ = 'validation_rules'
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if inspect.iscoroutinefunction(func):
            return await func(self, *args, **kwargs)
        return func(self, *args, **kwargs)
    return wrapper

def validate_input(input_class: Union[Type, List[Type]]):
    """
    Decorator to validate the input data, whether it's a single instance or a list of instances.
    
    Args:
        input_class (Union[Type, List[Type]]): The expected class or list of classes to validate against.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, input_data, *args, **kwargs):
            try:
                # If input_data is a list, validate each item in the list
                if isinstance(input_data, list):
                    for item in input_data:
                        if not isinstance(item, input_class):
                            raise ValueError(f"Each item in input_data must be an instance of {input_class}")
                        # Call all model_validator-decorated methods in each item
                        await _call_validators(item)
                # If input_data is a single instance, validate it
                elif isinstance(input_data, input_class):
                    await _call_validators(input_data)
                else:
                    raise ValueError(f"Input data must be an instance of {input_class} or a list of such instances")
            
            except ValueError as e:
                return ApiResponse(
                    status=False,
                    code=ResponseCode.BAD_REQUEST,
                    message=str(e),
                    data=None
                )
            except ValidationError as e:
                return ApiResponse(
                    status=False,
                    code=ResponseCode.BAD_REQUEST,
                    message=str(e),
                    errors=e.errors
                )
            return await func(self, input_data, *args, **kwargs)
        return wrapper
    return decorator


async def _call_validators(instance):
    """Calls all methods decorated with custom decorators, and identifies which decorator is applied."""
    for attr_name in dir(instance):
        attr = getattr(instance, attr_name)

        # Skip special methods (those starting and ending with '__')
        if attr_name.startswith('__') and attr_name.endswith('__'):
            continue

        # Check if the attribute is callable and has been wrapped by a decorator
        if callable(attr) and hasattr(attr, '__wrapped__'):
            # Check for the custom decorator name
            decorator_name = getattr(attr, '_decorator_name_', None)
            if decorator_name == 'validation_rules':
                # try:
                if inspect.iscoroutinefunction(attr):
                    rules = await attr()  # Call the async method
                else:
                    rules = attr()  # Call the regular function
                    
                await FieldValidator().validate(instance.__dict__, rules)
                # except ValidationError as e:
                #     raise ValueError(str(e))
            else:
                # Check if the method is asynchronous (a coroutine)
                if inspect.iscoroutinefunction(attr):
                    await attr()  # Call the async method
                else:
                    attr()  # Call the regular function
