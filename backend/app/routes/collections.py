"""
Collection explorer routes — show schema, indexes, and vector indexes for each collection.
Demonstrates MongoDB's introspection capabilities.
"""

from fastapi import APIRouter, HTTPException

from app.database import get_database
from app.utils.helpers import serialize_doc

router = APIRouter()

# Human-readable descriptions for each collection
COLLECTION_DESCRIPTIONS = {
    "payments": "Polymorphic payment messages (pacs.008, pacs.009, pacs.004, pain.001, pain.008)",
    "payment_initiations": "Batch payment initiation records (pain.001)",
    "status_reports": "FI-to-FI payment status reports (pacs.002) — TTL: 1 year",
    "statements": "End-of-day bank statements (camt.053)",
    "statement_entries": "Booked transaction entries within statements",
    "notifications": "Real-time debit/credit notifications (camt.054) — TTL: 90 days",
    "remittance_details": "Structured remittance data (remt.001) — separate collection to prevent unbounded growth",
    "investigations": "Exception handling and cancellation cases (camt.026-056)",
    "mandates": "Direct debit mandate lifecycle (pain.009-012)",
    "accounts": "Account master data (acmt.007)",
    "participants": "Financial institution registry (BIC directory)",
    "original_messages": "Raw XML message audit archive",
}

COLLECTION_ISO_TYPES = {
    "payments": ["pacs.008", "pacs.009", "pacs.004", "pain.001", "pain.008"],
    "payment_initiations": ["pain.001", "pain.008"],
    "status_reports": ["pacs.002"],
    "statements": ["camt.053"],
    "statement_entries": ["camt.053 entries"],
    "notifications": ["camt.054"],
    "remittance_details": ["remt.001"],
    "investigations": ["camt.026", "camt.029", "camt.056"],
    "mandates": ["pain.009", "pain.010", "pain.011", "pain.012"],
    "accounts": ["acmt.007"],
    "participants": [],
    "original_messages": [],
}


@router.get("/")
async def list_collections():
    """List all collections with document counts and descriptions."""
    db = get_database()
    names = await db.list_collection_names()
    # Filter out system collections
    names = [n for n in names if not n.startswith("system.")]
    names.sort()

    collections = []
    for name in names:
        count = await db[name].count_documents({})
        collections.append(
            {
                "name": name,
                "documentCount": count,
                "description": COLLECTION_DESCRIPTIONS.get(name, ""),
                "isoTypes": COLLECTION_ISO_TYPES.get(name, []),
            }
        )

    # Sort: known collections first (by description presence), then alphabetical
    collections.sort(key=lambda c: (0 if c["description"] else 1, c["name"]))

    return {
        "collections": collections,
        "total": len(collections),
    }


@router.get("/{name}")
async def get_collection_detail(name: str):
    """
    Get schema shape, regular indexes, and vector search indexes for a collection.
    """
    db = get_database()

    # Verify collection exists
    existing = await db.list_collection_names()
    if name not in existing:
        raise HTTPException(status_code=404, detail=f"Collection '{name}' not found")

    count = await db[name].count_documents({})

    # Get a sample document to infer schema shape
    sample = await db[name].find_one()
    schema_shape = _extract_schema(sample) if sample else {}

    # Get sample document (serialized, with large fields truncated)
    sample_doc = None
    if sample:
        serialized = serialize_doc(sample)
        sample_doc = _truncate_doc(serialized)

    # Get regular indexes
    regular_indexes = []
    async for idx in db[name].list_indexes():
        regular_indexes.append(
            {
                "name": idx.get("name", ""),
                "key": {k: _index_direction(v) for k, v in idx.get("key", {}).items()},
                "unique": idx.get("unique", False),
                "sparse": idx.get("sparse", False),
                "expireAfterSeconds": idx.get("expireAfterSeconds"),
            }
        )

    # Get vector / search indexes
    search_indexes = []
    try:
        async for idx in db[name].list_search_indexes():
            search_indexes.append(
                {
                    "name": idx.get("name", ""),
                    "type": idx.get("type", "search"),
                    "status": idx.get("status", ""),
                    "queryable": idx.get("queryable", False),
                    "latestDefinition": idx.get("latestDefinition", {}),
                }
            )
    except Exception:
        # list_search_indexes may not be available on all deployments
        pass

    # Get collection options (validator, capped, etc.)
    coll_options = {}
    try:
        coll_info = await db.command("listCollections", filter={"name": name})
        batches = coll_info.get("cursor", {}).get("firstBatch", [])
        if batches:
            coll_options = batches[0].get("options", {})
    except Exception:
        pass

    validator = coll_options.get("validator")
    validation_level = coll_options.get("validationLevel", "off")
    validation_action = coll_options.get("validationAction", "error")

    return {
        "name": name,
        "description": COLLECTION_DESCRIPTIONS.get(name, ""),
        "isoTypes": COLLECTION_ISO_TYPES.get(name, []),
        "documentCount": count,
        "schemaShape": schema_shape,
        "sampleDocument": sample_doc,
        "regularIndexes": regular_indexes,
        "searchIndexes": search_indexes,
        "validator": validator,
        "validationLevel": validation_level,
        "validationAction": validation_action,
    }


def _extract_schema(doc: dict, max_depth: int = 3, depth: int = 0) -> dict:
    """Extract a schema shape from a sample document showing field names and types."""
    if depth >= max_depth or not isinstance(doc, dict):
        return {}

    shape = {}
    for key, value in doc.items():
        if key == "_id":
            shape[key] = "ObjectId"
        elif isinstance(value, dict):
            nested = _extract_schema(value, max_depth, depth + 1)
            shape[key] = nested if nested else "Object"
        elif isinstance(value, list):
            if value and isinstance(value[0], dict):
                nested = _extract_schema(value[0], max_depth, depth + 1)
                shape[key] = (
                    f"Array<{{{', '.join(nested.keys())}}}>"
                    if nested
                    else "Array<Object>"
                )
            elif value:
                shape[key] = f"Array<{type(value[0]).__name__}>"
            else:
                shape[key] = "Array"
        elif value is None:
            shape[key] = "null"
        else:
            type_name = type(value).__name__
            # Make type names more readable
            type_map = {
                "str": "String",
                "int": "Int32",
                "float": "Double",
                "bool": "Boolean",
                "Decimal128": "Decimal128",
                "datetime": "Date",
                "ObjectId": "ObjectId",
            }
            shape[key] = type_map.get(type_name, type_name)
    return shape


def _truncate_doc(doc: dict, max_str_len: int = 80) -> dict:
    """Truncate large fields in a document for display."""
    result = {}
    for key, value in doc.items():
        if key in ("embedding", "remittanceEmbedding"):
            if isinstance(value, list) and len(value) > 0:
                result[key] = f"[{value[0]:.6f}, ... {len(value)} dimensions]"
            else:
                result[key] = value
        elif isinstance(value, str) and len(value) > max_str_len:
            result[key] = value[:max_str_len] + "..."
        elif isinstance(value, dict):
            result[key] = _truncate_doc(value, max_str_len)
        elif isinstance(value, list) and len(value) > 5:
            result[key] = value[:3] + [f"... +{len(value) - 3} more"]
        else:
            result[key] = value
    return result


def _index_direction(val) -> str:
    """Convert index direction to readable string."""
    if val == 1:
        return "ASC"
    elif val == -1:
        return "DESC"
    elif val == "text":
        return "TEXT"
    elif val == "2dsphere":
        return "2DSPHERE"
    return str(val)
