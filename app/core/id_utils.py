"""
ID normalization utilities.
"""


def normalize_uuid(value: str) -> str:
    """Normalize UUID strings to hex without dashes for DB lookups."""
    if not value:
        return value
    return value.replace("-", "").lower()
