"""Product error formatting around the standard JSON Schema validator."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from jsonschema.exceptions import SchemaError
from jsonschema.validators import validator_for
from referencing import Registry
from referencing.exceptions import Unresolvable


class ValidationError(ValueError):
    def __init__(self, message: str, errors: list[dict[str, Any]]) -> None:
        super().__init__(message)
        self.errors = errors


class ToolValidator:
    def __init__(self, schema_provider: Callable[[str], dict[str, Any] | None]) -> None:
        self._schema_provider = schema_provider

    def validate(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        errors = self.get_errors(tool_name, arguments)
        if errors:
            raise ValidationError(f"invalid arguments for tool '{tool_name}'", errors)
        return True

    def get_errors(self, tool_name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        schema = self._schema_provider(tool_name)
        if schema is None:
            return [{"path": [], "message": f"unknown tool: {tool_name}"}]
        if not isinstance(arguments, dict):
            return [{"path": [], "message": "tool arguments must be an object"}]
        try:
            validator_class = validator_for(schema)
            validator_class.check_schema(schema)
            # MCP schemas are untrusted. Resolve bundled/local references only;
            # validating arguments must never fetch URLs or read local files.
            validator = validator_class(schema, registry=Registry())
            return [
                {"path": list(error.absolute_path), "message": error.message}
                for error in validator.iter_errors(arguments)
            ]
        except SchemaError as exc:
            return [{"path": [], "message": f"invalid tool schema: {exc.message}"}]
        except Unresolvable:
            return [{"path": [], "message": "tool schema contains an unresolved reference"}]

    def sanitize(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.validate(tool_name, arguments)
        schema = self._schema_provider(tool_name) or {}
        # Preserve schema-permitted additional properties. Keep the existing
        # explicit property defaults visible to policy before execution.
        normalized: dict[str, Any] = self._apply_defaults(schema, deepcopy(arguments))
        self.validate(tool_name, normalized)
        return normalized

    def _apply_defaults(self, schema: dict[str, Any] | bool, value: Any) -> Any:
        """Legacy explicit property/item defaults, not a schema evaluator.

        JSON Schema defaults are annotations. Do not choose union branches or
        resolve references here; validation belongs entirely to jsonschema.
        """
        if not isinstance(schema, dict):
            return value
        if isinstance(value, dict):
            result = dict(value)
            for name, rule in schema.get("properties", {}).items():
                if name in result:
                    result[name] = self._apply_defaults(rule, result[name])
                elif isinstance(rule, dict) and "default" in rule:
                    result[name] = self._apply_defaults(rule, deepcopy(rule["default"]))
            return result
        if isinstance(value, list) and isinstance(schema.get("items"), dict):
            return [self._apply_defaults(schema["items"], item) for item in value]
        return value
