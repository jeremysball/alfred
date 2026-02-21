"""Base tool class with Pydantic schema generation."""

import json
from abc import ABC
from collections.abc import AsyncIterator
from typing import Any, TypeVar

from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo


class ToolParameter(BaseModel):
    """Base model for tool parameters."""

    class Config:
        extra = "forbid"


class ToolResult(BaseModel):
    """Base model for tool results."""

    success: bool = Field(default=True, description="Whether the tool executed successfully")
    error: str | None = Field(default=None, description="Error message if execution failed")

    class Config:
        extra = "allow"


class Tool(ABC):
    """Abstract base class for tools.

    Tools define their parameters using Pydantic models, which automatically
    generate JSON Schema for the LLM.
    """

    name: str
    description: str
    param_model: type[BaseModel] | None = None

    def __init__(self) -> None:
        self._param_model: type[BaseModel] | None = None
        self._init_param_model()

    def _init_param_model(self) -> None:
        """Initialize the Pydantic model from execute signature or param_model attr."""
        # Use explicit param_model if defined on the class
        if self.param_model is not None:
            self._param_model = self.param_model
            return

        import inspect

        sig = inspect.signature(self.execute)

        # Build field definitions for create_model
        fields: dict[str, Any] = {}

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            # Get type annotation
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else str

            # Get default or Field()
            if param.default == inspect.Parameter.empty:
                # Required field
                default = Field(...)
            elif isinstance(param.default, FieldInfo):
                # Already a Field()
                default = param.default
            else:
                # Has default value
                default = param.default

            fields[param_name] = (annotation, default)

        # Create the Pydantic model
        self._param_model = create_model(
            f"{self.__class__.__name__}Params", __base__=ToolParameter, **fields
        )

    def execute(self, **kwargs: Any) -> str | dict[str, Any]:
        """Execute the tool with the given parameters (non-streaming).

        Default implementation returns an error message. Override this method
        if the tool supports synchronous execution, or override execute_stream()
        for async-only tools.

        Args:
            **kwargs: Parameters as defined by the tool's schema

        Returns:
            Either a string or a dict (will be JSON-serialized)
        """
        return (
            f"Error: {self.__class__.__name__} must be called via execute_stream in async context"
        )

    async def execute_stream(self, **kwargs: Any) -> AsyncIterator[str]:
        """Execute the tool with streaming output.

        Yields output chunks as they become available. Default implementation
        calls execute() and yields the full result (override for true streaming).

        Args:
            **kwargs: Parameters as defined by the tool's schema

        Yields:
            Output chunks as strings
        """
        import asyncio

        # Run execute in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: self.execute(**kwargs))

        if isinstance(result, str):
            yield result
        else:
            yield json.dumps(result, indent=2)

    def get_schema(self) -> dict[str, Any]:
        """Get JSON Schema for this tool (OpenAI format)."""
        if self._param_model is None:
            raise RuntimeError("Parameter model not initialized")

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self._param_model.model_json_schema(),
            },
        }

    def validate_and_run(self, arguments: dict[str, Any]) -> str | dict[str, Any]:
        """Validate arguments and execute the tool (non-streaming).

        Args:
            arguments: Raw arguments from LLM (will be validated)

        Returns:
            Tool result
        """
        if self._param_model is None:
            raise RuntimeError("Parameter model not initialized")

        # Validate with Pydantic
        validated = self._param_model(**arguments)

        # Execute with validated params
        return self.execute(**validated.model_dump())

    async def validate_and_run_stream(self, arguments: dict[str, Any]) -> AsyncIterator[str]:
        """Validate arguments and execute the tool with streaming.

        Args:
            arguments: Raw arguments from LLM (will be validated)

        Yields:
            Output chunks as strings
        """
        if self._param_model is None:
            raise RuntimeError("Parameter model not initialized")

        # Validate with Pydantic
        validated = self._param_model(**arguments)

        # Execute with streaming
        async for chunk in self.execute_stream(**validated.model_dump()):
            yield chunk


# Type variable for generic tool creation
T = TypeVar("T", bound=Tool)
