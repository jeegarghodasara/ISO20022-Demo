"""
Tool Call Logger — audit trail of every database operation agents execute.

MongoDB VALUE PROP: Append-only audit log with TTL.
Every aggregation, find, and vector search is recorded for compliance.
"""

import uuid
from datetime import datetime, timezone

from app.database import get_database
from app.utils.helpers import serialize_doc


async def log_tool_call(
    agent_id: str,
    conversation_id: str,
    tool_name: str,
    tool_input: dict,
    tool_output_summary: str = None,
    latency_ms: float = None,
) -> None:
    """Log a single tool/DB operation executed by an agent."""
    db = get_database()

    log_entry = {
        "logId": str(uuid.uuid4()),
        "agentId": agent_id,
        "conversationId": conversation_id,
        "toolName": tool_name,
        "toolInput": tool_input,
        "outputSummary": tool_output_summary,
        "latencyMs": latency_ms,
        "timestamp": datetime.now(timezone.utc),
    }

    await db.agent_tool_logs.insert_one(log_entry)


async def get_tool_logs(agent_id: str = None, limit: int = 50) -> list:
    """Get recent tool call logs, optionally filtered by agent."""
    db = get_database()
    query = {"agentId": agent_id} if agent_id else {}
    cursor = (
        db.agent_tool_logs.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit)
    )
    return [serialize_doc(doc) async for doc in cursor]


async def get_tool_stats() -> dict:
    """
    Compute tool usage statistics per agent.

    MongoDB VALUE PROP: Aggregation for audit analytics.
    """
    db = get_database()

    pipeline = [
        {
            "$group": {
                "_id": {"agentId": "$agentId", "toolName": "$toolName"},
                "count": {"$sum": 1},
                "avgLatencyMs": {"$avg": "$latencyMs"},
            }
        },
        {"$sort": {"count": -1}},
    ]

    cursor = db.agent_tool_logs.aggregate(pipeline)
    stats = [serialize_doc(doc) async for doc in cursor]
    return stats
