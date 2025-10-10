#!/usr/bin/env python3
"""
Schema Generation Script for PropPal
Generates TypeScript interfaces from Pydantic models
"""
import json
import os
from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from pydantic_core import core_schema

# Import all models
from models import (
    # Users
    UserResponse,
    UserCreate,
    # Properties
    PropertyResponse,
    PropertyCreate,
    # Property Amenities
    PropertyAmenityResponse,
    PropertyAmenityCreate,
    # Builder Profiles
    BuilderProfileResponse,
    BuilderProfileCreate,
    # Builder Services
    BuilderServiceResponse,
    BuilderServiceCreate,
    # User Projects
    UserProjectResponse,
    UserProjectCreate,
    # Builder Bids
    BuilderBidResponse,
    BuilderBidCreate,
    # Visits
    VisitResponse,
    VisitCreate,
    # Projects
    ProjectResponse,
    ProjectCreate,
    # Query Logs
    QueryLogResponse,
    QueryLogCreate,
    # Chat Histories
    ChatHistoryResponse,
    ChatHistoryCreate,
    ChatMessage,
)


def pydantic_to_ts_type(python_type: str) -> str:
    """Convert Python/JSON Schema types to TypeScript"""
    type_mapping = {
        "string": "string",
        "integer": "number",
        "number": "number",
        "boolean": "boolean",
        "array": "Array",
        "object": "Record<string, any>",
        "null": "null",
    }
    return type_mapping.get(python_type, "any")


def json_schema_to_ts_interface(
    name: str, schema: Dict[str, Any], indent: int = 0
) -> str:
    """Convert JSON schema to TypeScript interface"""
    lines = []
    ind = "  " * indent

    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    for prop_name, prop_schema in properties.items():
        prop_type = prop_schema.get("type", "any")
        description = prop_schema.get("description")

        if description:
            lines.append(f"{ind}  /** {description} */")

        # Handle anyOf at property level (e.g., Optional[List[str]])
        if "anyOf" in prop_schema and prop_type == "any":
            # Find the non-null type in anyOf
            for option in prop_schema["anyOf"]:
                if option.get("type") and option.get("type") != "null":
                    prop_type = option.get("type")
                    if prop_type == "array":
                        prop_schema = option  # Use this option's schema
                    elif prop_type == "object":
                        prop_schema = option
                    break

        # Handle arrays
        if prop_type == "array":
            item_schema = prop_schema.get("items", {})
            # Handle case where items might have anyOf (union types)
            if "anyOf" in item_schema:
                # Extract type from anyOf, typically for Optional types
                types = []
                for t in item_schema["anyOf"]:
                    if "type" in t and t["type"] != "null":
                        types.append(pydantic_to_ts_type(t["type"]))
                item_type_str = types[0] if types else "any"
                ts_type = f"{item_type_str}[]"
            else:
                item_type = item_schema.get("type", "string")  # Default to string for arrays
                if item_type == "object":
                    ts_type = "Record<string, any>[]"
                else:
                    ts_type = f"{pydantic_to_ts_type(item_type)}[]"
        # Handle objects
        elif prop_type == "object":
            ts_type = "Record<string, any>"
        # Handle ObjectId (special case)
        elif prop_schema.get("format") == "objectid":
            ts_type = "string"
        # Handle anyOf (union types)
        elif "anyOf" in prop_schema:
            types = [
                pydantic_to_ts_type(t.get("type", "any"))
                for t in prop_schema["anyOf"]
            ]
            ts_type = " | ".join(types)
        else:
            ts_type = pydantic_to_ts_type(prop_type)

        # Check if optional
        optional = "" if prop_name in required else "?"

        lines.append(f"{ind}  {prop_name}{optional}: {ts_type};")

    return "\n".join(lines)


def generate_typescript_interfaces():
    """Generate TypeScript interfaces from all Pydantic models"""

    # Models to export
    models = {
        # Users
        "UserResponse": UserResponse,
        "UserCreate": UserCreate,
        # Properties
        "PropertyResponse": PropertyResponse,
        "PropertyCreate": PropertyCreate,
        # Property Amenities
        "PropertyAmenityResponse": PropertyAmenityResponse,
        "PropertyAmenityCreate": PropertyAmenityCreate,
        # Builder Profiles
        "BuilderProfileResponse": BuilderProfileResponse,
        "BuilderProfileCreate": BuilderProfileCreate,
        # Builder Services
        "BuilderServiceResponse": BuilderServiceResponse,
        "BuilderServiceCreate": BuilderServiceCreate,
        # User Projects
        "UserProjectResponse": UserProjectResponse,
        "UserProjectCreate": UserProjectCreate,
        # Builder Bids
        "BuilderBidResponse": BuilderBidResponse,
        "BuilderBidCreate": BuilderBidCreate,
        # Visits
        "VisitResponse": VisitResponse,
        "VisitCreate": VisitCreate,
        # Projects
        "ProjectResponse": ProjectResponse,
        "ProjectCreate": ProjectCreate,
        # Query Logs
        "QueryLogResponse": QueryLogResponse,
        "QueryLogCreate": QueryLogCreate,
        # Chat Histories
        "ChatHistoryResponse": ChatHistoryResponse,
        "ChatHistoryCreate": ChatHistoryCreate,
        "ChatMessage": ChatMessage,
    }

    # Output file path
    output_dir = Path("../../packages/schemas/generated")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "models.ts"

    # Generate TypeScript
    ts_content = [
        "/**",
        " * AUTO-GENERATED TypeScript interfaces from Pydantic models",
        " * DO NOT EDIT MANUALLY - Changes will be overwritten",
        f" * Generated on: {__import__('datetime').datetime.now().isoformat()}",
        " */",
        "",
    ]

    for model_name, model_class in models.items():
        # Get JSON schema
        schema = model_class.model_json_schema()

        # Generate interface
        ts_content.append(f"export interface {model_name} {{")
        ts_content.append(json_schema_to_ts_interface(model_name, schema))
        ts_content.append("}")
        ts_content.append("")

    # Write to file
    with open(output_file, "w") as f:
        f.write("\n".join(ts_content))

    print(f"[SUCCESS] TypeScript interfaces generated successfully!")
    print(f"[OUTPUT] {output_file}")
    print(f"[INFO] Generated {len(models)} interfaces")


if __name__ == "__main__":
    generate_typescript_interfaces()

