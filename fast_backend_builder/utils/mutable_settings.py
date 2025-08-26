from datetime import time
import inspect
from fastapi import APIRouter, HTTPException, FastAPI, Request
from typing import Dict, Any, Union, List, Callable
from decimal import Decimal

from pydantic import BaseModel

from fast_backend_builder.auth.middleware import authorize


# Decorators for field properties
def mutable(mutable: bool = True):
    def decorator(field):
        field._mutable = mutable
        return field
    return decorator


def description(desc: str):
    def decorator(field):
        field._description = desc
        return field
    return decorator


def enum_values(values: List[str]):
    def decorator(field):
        field._enum_values = values
        return field
    return decorator


def field_type(ftype: str):
    def decorator(field):
        field._field_type = ftype
        return field
    return decorator


def name(n: str):
    def decorator(field):
        field._name = n
        return field
    return decorator

def on_change(callback: Callable):
    """
    A decorator to register a callback function that is executed whenever the setting changes.
    """
    def decorator(field):
        field._on_change = callback
        return field
    return decorator


# Custom UpdateRequest class
class UpdateSettingRequest(BaseModel):
    value: Union[str, bool, int, float, Decimal, time]


# The Modifiable superclass that handles dynamic routes and settings
class MutableSettings:
    """
    Base class for dynamically defining and managing application settings.
    
    This class extracts metadata from the extending class and registers FastAPI routes
    for retrieving/updating settings and calling callbacks.
    
    Example:
        class MySettings(MutableSettings):
            @field_type("boolean")
            @mutable(True)
            @description("Enable or disable feature X")
            @name("feature_x_enabled")
            def feature_x_enabled():
                return True
                
            @field_type("callback")
            @description("Calls function x")
            def call_x():
                x()
    """
    def __init__(self, app: FastAPI):
        self.router = APIRouter()

        # Automatically extract configurations from the extending class
        self.configurations = self._generate_configurations()
        self.add_get_routes()
        self.add_post_routes()

        # Include the router in the app
        app.include_router(self.router, prefix="/settings")

    def _generate_configurations(self) -> Dict[str, Dict[str, Any]]:
        """
        Generates a configuration dictionary from class attributes.
        """
        configurations = {}
        for attr_name, attr_value in self.__class__.__dict__.items():
            if not attr_name.startswith("__") and callable(attr_value):
                # Call the field function to get the default value
                if getattr(attr_value, "_field_type", None) != "callback":
                    default_value = attr_value()
                else: default_value = None
                
                field_info = {
                    "type": getattr(attr_value, "_field_type", "callback" if callable(default_value) else type(default_value).__name__),
                    "value": default_value,
                    "default_value": default_value,
                    "description": getattr(attr_value, "_description", ""),
                    "mutable": getattr(attr_value, "_mutable", False),
                    "enum_values": getattr(attr_value, "_enum_values", []),
                    "name": getattr(attr_value, "_name", attr_name),
                    "on_change": getattr(attr_value, "_on_change", None),
                }
                configurations[field_info["name"]] = field_info
        return configurations

    def add_get_routes(self):
        @self.router.get("", summary="Get all settings", tags=["MutableSettings"])
        @authorize(['view_system_settings'])
        async def get_all_settings(request: Request):
            return self.configurations

        for key, config in self.configurations.items():
            if config["type"] == "enum":
                @self.router.get(f"/{key}/options", summary=f"Get enum options for {key}", tags=["MutableSettings"])
                @authorize(['view_system_settings'])
                async def get_enum_options(config_key=key):
                    enum_values = self.configurations[config_key].get("enum_values")
                    if enum_values:
                        return {"enum_values": enum_values}
                    raise HTTPException(status_code=404, detail="Enum values not found")

    def add_post_routes(self):
        @self.router.post("/{key}", summary="Update a setting", tags=["MutableSettings"])
        @authorize(['change_system_settings'])
        async def update_setting(request: Request, key: str, body: UpdateSettingRequest):
            if key not in self.configurations:
                raise HTTPException(status_code=404, detail="Setting not found")

            config = self.configurations[key]
            value = body.value

            if config["type"] == "callback":
                # Directly invoke the field function
                field_function = getattr(self.__class__, config["name"], None)
                if not field_function:
                    raise HTTPException(status_code=404, detail="Field function not found")
                if inspect.iscoroutinefunction(field_function):
                    result = await field_function()
                else:
                    result = field_function()
                return {"message": "Callback executed", "result": result}

            if not config["mutable"]:
                raise HTTPException(status_code=403, detail="This setting is not mutable")

            # Type validation
            if config["type"] == "boolean" and not isinstance(value, bool):
                raise HTTPException(status_code=400, detail="Invalid value for boolean setting")
            if config["type"] == "integer" and not isinstance(value, int):
                raise HTTPException(status_code=400, detail="Invalid value for integer setting")
            if config["type"] == "decimal" and not isinstance(value, (float, Decimal)):
                raise HTTPException(status_code=400, detail="Invalid value for decimal setting")
            if config["type"] == "float" and not isinstance(value, float):
                raise HTTPException(status_code=400, detail="Invalid value for float setting")
            if config["type"] == "time":
                try:
                    value = time.fromisoformat(value)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM:SS.")
            if config["type"] == "enum" and value not in config.get("enum_values", []):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid value. Allowed values: {config.get('enum_values', [])}",
                )

            # Update the value
            config["value"] = value
            setattr(self.__class__, config["name"], lambda: value)

            # Execute the on_change callback if defined
            on_change_callback = config.get("on_change")
            if on_change_callback:
                if inspect.iscoroutinefunction(on_change_callback):
                    await on_change_callback()
                else:
                    on_change_callback()

            return {"message": "Setting updated", "key": key, "value": value}
