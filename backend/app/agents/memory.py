"""
Agent Memory Service — MongoDB-backed memory with three types.

Episodic:   Individual events/decisions (TTL: 90 days)
Semantic:   Aggregated knowledge (permanent)
Procedural: Workflow templates and decision rules (permanent)

Uses MongoDB Vector Search for semantic memory retrieval,
recency weighting, and frequency boosting.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.database import get_database
from app.utils.helpers import serialize_doc
from app.utils.embeddings import embed_texts, embed_query, EMBEDDING_DIMENSIONS

MEMORY_VECTOR_INDEX = "memory_vector_index"


async def store_memory(
    agent_id: str,
    memory_type: str,
    content: str,
    context: dict = None,
    conversation_id: str = None,
    ttl_days: int = None,
) -> dict:
    """Store a new memory for an agent."""
    db = get_database()
    now = datetime.now(timezone.utc)

    # Generate embedding for the content
    try:
        embeddings = embed_texts([content])
        embedding = embeddings[0]
    except Exception:
        embedding = None

    memory = {
        "memoryId": str(uuid.uuid4()),
        "agentId": agent_id,
        "memoryType": memory_type,
        "content": content,
        "context": context or {},
        "conversationId": conversation_id,
        "embedding": embedding,
        "relevanceScore": 1.0,
        "accessCount": 0,
        "createdAt": now,
        "lastAccessedAt": now,
    }

    # Set TTL for episodic memory
    if ttl_days or memory_type == "episodic":
        days = ttl_days or 90
        memory["expiresAt"] = now + timedelta(days=days)

    await db.agent_memory.insert_one(memory)
    return serialize_doc(memory)


async def recall_memories(
    agent_id: str,
    query: str,
    memory_type: str = None,
    limit: int = 5,
) -> List[dict]:
    """
    Recall relevant memories using vector similarity + recency + frequency.

    MongoDB VALUE PROP: Vector Search for agent memory retrieval.
    Combines semantic similarity with recency decay and frequency boosting
    in a single aggregation pipeline.
    """
    db = get_database()

    # Generate query embedding
    try:
        query_embedding = embed_query(query)
    except Exception:
        # Fallback to text-based search if embedding fails
        return await _text_recall(agent_id, query, memory_type, limit)

    # Build vector search with optional filter
    vs_filter = {"agentId": agent_id}
    if memory_type:
        vs_filter["memoryType"] = memory_type

    pipeline = [
        {
            "$vectorSearch": {
                "index": MEMORY_VECTOR_INDEX,
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": limit * 20,
                "limit": limit * 3,  # fetch more, then re-rank
                "filter": vs_filter,
            }
        },
        {
            "$addFields": {
                "vectorScore": {"$meta": "vectorSearchScore"},
                "recencyDays": {
                    "$dateDiff": {
                        "startDate": "$lastAccessedAt",
                        "endDate": "$$NOW",
                        "unit": "day",
                    }
                },
            }
        },
        {
            "$addFields": {
                "recencyBoost": {"$divide": [1, {"$add": [1, "$recencyDays"]}]},
                "frequencyBoost": {
                    "$multiply": [
                        {"$log": [{"$add": ["$accessCount", 2]}, 10]},
                        0.1,
                    ]
                },
            }
        },
        {
            "$addFields": {
                "finalScore": {
                    "$add": [
                        {"$multiply": ["$vectorScore", 0.7]},
                        {"$multiply": ["$recencyBoost", 0.2]},
                        "$frequencyBoost",
                    ]
                }
            }
        },
        {"$sort": {"finalScore": -1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 0,
                "memoryId": 1,
                "agentId": 1,
                "memoryType": 1,
                "content": 1,
                "context": 1,
                "vectorScore": 1,
                "recencyBoost": 1,
                "frequencyBoost": 1,
                "finalScore": 1,
                "accessCount": 1,
                "createdAt": 1,
                "lastAccessedAt": 1,
            }
        },
    ]

    try:
        cursor = db.agent_memory.aggregate(pipeline)
        memories = [serialize_doc(doc) async for doc in cursor]
    except Exception:
        # If vector search index not ready, fallback
        memories = await _text_recall(agent_id, query, memory_type, limit)
        return memories

    # Update access counts for recalled memories
    memory_ids = [m["memoryId"] for m in memories]
    if memory_ids:
        await db.agent_memory.update_many(
            {"memoryId": {"$in": memory_ids}},
            {
                "$inc": {"accessCount": 1},
                "$set": {"lastAccessedAt": datetime.now(timezone.utc)},
            },
        )

    return memories


async def _text_recall(agent_id, query, memory_type, limit):
    """Fallback text-based recall when vector search is unavailable."""
    db = get_database()
    filter_q = {"agentId": agent_id}
    if memory_type:
        filter_q["memoryType"] = memory_type

    cursor = db.agent_memory.find(filter_q).sort("lastAccessedAt", -1).limit(limit)
    return [serialize_doc(doc) async for doc in cursor]


async def get_agent_memories(
    agent_id: str,
    memory_type: str = None,
    limit: int = 20,
) -> List[dict]:
    """Get recent memories for an agent (for memory inspector)."""
    db = get_database()
    filter_q = {"agentId": agent_id}
    if memory_type:
        filter_q["memoryType"] = memory_type

    cursor = (
        db.agent_memory.find(filter_q, {"embedding": 0})
        .sort("createdAt", -1)
        .limit(limit)
    )
    return [serialize_doc(doc) async for doc in cursor]


async def get_memory_stats() -> dict:
    """Get memory statistics across all agents."""
    db = get_database()
    pipeline = [
        {
            "$group": {
                "_id": {"agentId": "$agentId", "memoryType": "$memoryType"},
                "count": {"$sum": 1},
                "avgAccessCount": {"$avg": "$accessCount"},
            }
        },
        {"$sort": {"_id.agentId": 1}},
    ]
    cursor = db.agent_memory.aggregate(pipeline)
    stats = [serialize_doc(doc) async for doc in cursor]
    return stats
