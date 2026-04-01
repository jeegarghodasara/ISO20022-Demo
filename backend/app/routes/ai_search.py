"""
AI-powered search routes using MongoDB Vector Search + Voyage AI embeddings.

Three use cases:
1. Natural Language Payment Search - describe what you're looking for
2. Similar Transaction Detection - find payments similar to a flagged one
3. Smart Remittance Matching - match payments to invoices semantically
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.database import get_database
from app.utils.helpers import serialize_doc
from app.utils.embeddings import (
    embed_query,
    payment_to_text,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
)

router = APIRouter()

VECTOR_INDEX_NAME = "payment_vector_index"
REMITTANCE_INDEX_NAME = "remittance_vector_index"


@router.get("/status")
async def ai_search_status():
    """Check if vector search is ready (embeddings exist, index accessible)."""
    db = get_database()
    total = await db.payments.count_documents({})
    embedded = await db.payments.count_documents({"embedding": {"$exists": True}})

    return {
        "ready": embedded > 0,
        "totalPayments": total,
        "embeddedPayments": embedded,
        "coverage": f"{embedded / total * 100:.0f}%" if total > 0 else "0%",
        "model": EMBEDDING_MODEL,
        "dimensions": EMBEDDING_DIMENSIONS,
        "indexes": {
            "payment": VECTOR_INDEX_NAME,
            "remittance": REMITTANCE_INDEX_NAME,
        },
    }


@router.post("/natural-language")
async def natural_language_search(body: dict):
    """
    Use Case 1: Natural Language Payment Search

    MongoDB VALUE PROP: Vector Search on Polymorphic Data
    Search across ALL payment types using natural language descriptions.
    "large transfers to Germany that failed" finds relevant pacs.008, pacs.009 etc.
    without needing to know field names or ISO codes.
    """
    db = get_database()
    query_text = body.get("query", "").strip()
    limit = body.get("limit", 10)
    message_type_filter = body.get("messageType")

    if not query_text:
        raise HTTPException(status_code=400, detail="Query text is required")

    # Embed the user's natural language query
    query_embedding = embed_query(query_text)

    # Build the vector search pipeline
    vector_search_stage = {
        "$vectorSearch": {
            "index": VECTOR_INDEX_NAME,
            "path": "embedding",
            "queryVector": query_embedding,
            "numCandidates": limit * 20,
            "limit": limit,
        }
    }

    # Add pre-filter if message type specified
    if message_type_filter:
        vector_search_stage["$vectorSearch"]["filter"] = {
            "messageType": message_type_filter
        }

    pipeline = [
        vector_search_stage,
        {
            "$project": {
                "_id": 0,
                "uetr": 1,
                "messageType": 1,
                "settlementAmount": 1,
                "settlementCurrency": 1,
                "status": 1,
                "priority": 1,
                "debtor": 1,
                "creditor": 1,
                "debtorAgent": 1,
                "creditorAgent": 1,
                "settlementDate": 1,
                "direction": 1,
                "remittanceSummary": 1,
                "returnReason": 1,
                "mandateId": 1,
                "embeddingText": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    cursor = db.payments.aggregate(pipeline)
    results = [serialize_doc(doc) async for doc in cursor]

    return {
        "query": query_text,
        "results": results,
        "total": len(results),
        "model": EMBEDDING_MODEL,
    }


@router.post("/similar-transactions")
async def find_similar_transactions(body: dict):
    """
    Use Case 2: Similar Transaction / Anomaly Detection

    MongoDB VALUE PROP: Vector Search for Pattern Matching
    Given a flagged payment, find structurally similar transactions.
    Uses the payment's embedding to find nearest neighbors in vector space.
    Useful for fraud detection: "show me payments that look like this suspicious one."
    """
    db = get_database()
    uetr = body.get("uetr", "").strip()
    limit = body.get("limit", 10)
    exclude_self = body.get("excludeSelf", True)

    if not uetr:
        raise HTTPException(status_code=400, detail="Payment UETR is required")

    # Fetch the reference payment
    reference = await db.payments.find_one({"uetr": uetr})
    if not reference:
        raise HTTPException(status_code=404, detail="Payment not found")

    reference_embedding = reference.get("embedding")

    if not reference_embedding:
        # Generate embedding on the fly if not stored
        text = payment_to_text(serialize_doc(reference))
        reference_embedding = embed_query(text)

    # Search for similar payments
    search_limit = limit + 1 if exclude_self else limit

    pipeline = [
        {
            "$vectorSearch": {
                "index": VECTOR_INDEX_NAME,
                "path": "embedding",
                "queryVector": reference_embedding,
                "numCandidates": search_limit * 20,
                "limit": search_limit,
            }
        },
        {
            "$project": {
                "_id": 0,
                "uetr": 1,
                "messageType": 1,
                "settlementAmount": 1,
                "settlementCurrency": 1,
                "status": 1,
                "priority": 1,
                "debtor": 1,
                "creditor": 1,
                "debtorAgent": 1,
                "creditorAgent": 1,
                "settlementDate": 1,
                "direction": 1,
                "embeddingText": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    cursor = db.payments.aggregate(pipeline)
    results = [serialize_doc(doc) async for doc in cursor]

    # Optionally exclude the reference payment itself
    if exclude_self:
        results = [r for r in results if r.get("uetr") != uetr][:limit]

    ref_serialized = serialize_doc(reference)
    ref_serialized.pop("embedding", None)
    ref_serialized.pop("remittanceEmbedding", None)

    return {
        "reference": {
            "uetr": ref_serialized.get("uetr"),
            "messageType": ref_serialized.get("messageType"),
            "settlementAmount": ref_serialized.get("settlementAmount"),
            "settlementCurrency": ref_serialized.get("settlementCurrency"),
            "status": ref_serialized.get("status"),
            "debtor": ref_serialized.get("debtor"),
            "creditor": ref_serialized.get("creditor"),
            "embeddingText": ref_serialized.get("embeddingText"),
        },
        "similar": results,
        "total": len(results),
    }


@router.post("/remittance-match")
async def smart_remittance_match(body: dict):
    """
    Use Case 3: Smart Remittance Matching

    MongoDB VALUE PROP: Vector Search for Fuzzy Matching
    Match incoming payment descriptions to existing records semantically.
    Handles typos, abbreviations, and partial references that exact match would miss.
    E.g., "Invoice 2026-42 from ACME" matches "INV-2026-0042 ACME Corp supplies"
    """
    db = get_database()
    query_text = body.get("query", "").strip()
    limit = body.get("limit", 10)

    if not query_text:
        raise HTTPException(status_code=400, detail="Remittance text is required")

    # Embed the remittance query
    query_embedding = embed_query(query_text)

    pipeline = [
        {
            "$vectorSearch": {
                "index": REMITTANCE_INDEX_NAME,
                "path": "remittanceEmbedding",
                "queryVector": query_embedding,
                "numCandidates": limit * 20,
                "limit": limit,
            }
        },
        {
            "$project": {
                "_id": 0,
                "uetr": 1,
                "messageType": 1,
                "settlementAmount": 1,
                "settlementCurrency": 1,
                "status": 1,
                "debtor": 1,
                "creditor": 1,
                "settlementDate": 1,
                "remittanceSummary": 1,
                "remittanceEmbeddingText": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    cursor = db.payments.aggregate(pipeline)
    results = [serialize_doc(doc) async for doc in cursor]

    return {
        "query": query_text,
        "results": results,
        "total": len(results),
        "model": EMBEDDING_MODEL,
    }
