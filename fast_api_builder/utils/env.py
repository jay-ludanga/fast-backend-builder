from typing import Callable, Generic, Optional, TypeVar
from decouple import config, UndefinedValueError
from fast_api_builder.utils.error_logging import log_exception

T = TypeVar("T")

def env_var(name: str, cast: Optional[Callable[[str], T]] = None, default: Optional[T] = None) -> T:
    """
    Fetch an environment variable with optional casting and a default value.
    
    :param name: Name of the environment variable.
    :param cast: Callable for casting the environment variable's value.
    :param default: Default value if the environment variable is undefined.
    :return: The environment variable value, cast to the specified type, or the default.
    """
    try:
        # Fetch with casting and default value
        if cast and default is not None:
            return config(name, cast=cast, default=default)
        # Fetch with only casting
        elif cast:
            return config(name, cast=cast)
        # Fetch with only default value
        elif default is not None:
            return config(name, default=default)
        # Fetch without default (will raise error if missing)
        else:
            return config(name)  # Raises error if the env variable is not found
    except Exception as e:
        log_exception(f"{str(e)}")
        # Return the default value if provided, otherwise None
        if default is not None:
            return default
        return None  # Explicitly return None if no default is specified
    
    except UndefinedValueError as e:
        log_exception(f"{str(e)}")
        # Return the default value if provided, otherwise None
        if default is not None:
            return default
        return None  # Explicitly return None if no default is specified