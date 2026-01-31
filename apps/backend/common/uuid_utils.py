"""Parse UUID from path/query and raise 404 on invalid."""

import uuid

from fastapi import HTTPException, status


def parse_uuid(value: str, name: str = "id") -> str:
    """
    Parse a string as UUID; raise 404 if invalid.
    Use for path/query parameters.
    """
    try:
        parsed = uuid.UUID(value)
        return str(parsed)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invalid or unknown {name}",
        ) from None
