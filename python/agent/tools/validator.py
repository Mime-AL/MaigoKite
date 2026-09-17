"""JSON-Schema validation for tool arguments."""
from __future__ import annotations
from typing import Any, Callable
import re
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
        errors: list[dict[str, Any]] = []
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in arguments:
                errors.append({"path": [name], "message": "required property is missing"})
        for name, value in arguments.items():
            rule = properties.get(name)
            if rule is None:
                errors.append({"path": [name], "message": "additional property is not allowed"})
                continue
            expected = rule.get("type")
            if expected is None and "anyOf" in rule:
                alternatives = [item.get("type") for item in rule["anyOf"]]
                if value is None and "null" in alternatives:
                    continue
                expected = next((item for item in alternatives if item != "null"), None)
            types = {
                "string": str, "integer": int, "number": (int, float),
                "boolean": bool, "object": dict, "array": list,
            }
            if expected in types and (not isinstance(value, types[expected]) or expected == "integer" and isinstance(value, bool)):
                errors.append({"path": [name], "message": f"must be {expected}"})
            if "enum" in rule and value not in rule["enum"]:
                errors.append({"path": [name], "message": "value is not in enum"})
            if isinstance(value, str):
                if len(value) < rule.get("minLength", 0): errors.append({"path":[name],"message":"string is too short"})
                if len(value) > rule.get("maxLength", 1_000_000): errors.append({"path":[name],"message":"string is too long"})
                if rule.get("pattern") and re.fullmatch(rule["pattern"],value) is None: errors.append({"path":[name],"message":"string does not match pattern"})
            if isinstance(value,(int,float)) and not isinstance(value,bool):
                if "minimum" in rule and value<rule["minimum"]: errors.append({"path":[name],"message":"number is below minimum"})
                if "maximum" in rule and value>rule["maximum"]: errors.append({"path":[name],"message":"number is above maximum"})
        return errors

    def sanitize(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.validate(tool_name, arguments)
        allowed = set((self._schema_provider(tool_name) or {}).get("properties", {}))
        return {key: value for key, value in arguments.items() if key in allowed}
