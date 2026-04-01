import uuid
from datetime import datetime, timezone
from decimal import Decimal
from bson import Decimal128, ObjectId


def generate_uetr() -> str:
    """Generate a UUID v4 UETR (Unique End-to-end Transaction Reference)."""
    return str(uuid.uuid4())


def generate_message_id(prefix: str = "MSG") -> str:
    """Generate a unique message ID."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    short = uuid.uuid4().hex[:8]
    return f"{prefix}-{ts}-{short}"


def to_decimal128(value) -> Decimal128:
    """Convert a value to Decimal128 for MongoDB monetary storage."""
    if isinstance(value, Decimal128):
        return value
    return Decimal128(str(value))


def from_decimal128(value) -> float:
    """Convert Decimal128 to float for JSON serialization."""
    if isinstance(value, Decimal128):
        return float(str(value))
    return float(value) if value else 0.0


def serialize_doc(doc: dict) -> dict:
    """Serialize a MongoDB document for JSON response."""
    if doc is None:
        return None
    result = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, Decimal128):
            result[key] = float(str(value))
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = serialize_doc(value)
        elif isinstance(value, list):
            result[key] = [
                serialize_doc(v)
                if isinstance(v, dict)
                else str(v)
                if isinstance(v, ObjectId)
                else float(str(v))
                if isinstance(v, Decimal128)
                else v.isoformat()
                if isinstance(v, datetime)
                else v
                for v in value
            ]
        else:
            result[key] = value
    return result


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
