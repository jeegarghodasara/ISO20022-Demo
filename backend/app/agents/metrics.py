"""
Agent Performance Metrics — track latency, invocation counts, memory usage,
and decision distribution per agent.

MongoDB VALUE PROP: Atomic $inc and $push for real-time metric collection.
Aggregation pipelines compute dashboards entirely server-side.
"""

import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from app.database import get_database
from app.utils.helpers import serialize_doc


@asynccontextmanager
async def track_agent_execution(agent_id: str, conversation_id: str = None):
    """
    Context manager that tracks agent execution time and stores metrics.

    Usage:
        async with track_agent_execution("routing-agent", conv_id) as tracker:
            result = await do_work()
            tracker["decision"] = result.get("decision")
            tracker["memoriesUsed"] = result.get("memoriesUsed", 0)
    """
    tracker = {
        "decision": None,
        "memoriesUsed": 0,
        "error": None,
    }
    start = time.monotonic()

    try:
        yield tracker
    except Exception as e:
        tracker["error"] = str(e)
        raise
    finally:
        elapsed_ms = (time.monotonic() - start) * 1000
        db = get_database()
        now = datetime.now(timezone.utc)

        metric = {
            "agentId": agent_id,
            "conversationId": conversation_id,
            "timestamp": now,
            "latencyMs": round(elapsed_ms, 1),
            "memoriesUsed": tracker.get("memoriesUsed", 0),
            "decision": tracker.get("decision"),
            "success": tracker.get("error") is None,
            "error": tracker.get("error"),
        }

        await db.agent_metrics.insert_one(metric)


async def get_agent_metrics_summary() -> dict:
    """
    Compute agent performance metrics via aggregation pipeline.

    MongoDB VALUE PROP: Server-side analytics via $facet.
    One pipeline computes per-agent stats, overall stats, and hourly trends.
    """
    db = get_database()

    pipeline = [
        {
            "$facet": {
                "perAgent": [
                    {
                        "$group": {
                            "_id": "$agentId",
                            "totalInvocations": {"$sum": 1},
                            "avgLatencyMs": {"$avg": "$latencyMs"},
                            "maxLatencyMs": {"$max": "$latencyMs"},
                            "minLatencyMs": {"$min": "$latencyMs"},
                            "p95LatencyMs": {
                                "$percentile": {
                                    "input": "$latencyMs",
                                    "p": [0.95],
                                    "method": "approximate",
                                }
                            },
                            "totalMemoriesUsed": {"$sum": "$memoriesUsed"},
                            "avgMemoriesUsed": {"$avg": "$memoriesUsed"},
                            "successCount": {"$sum": {"$cond": ["$success", 1, 0]}},
                            "errorCount": {"$sum": {"$cond": ["$success", 0, 1]}},
                        }
                    },
                    {"$sort": {"totalInvocations": -1}},
                ],
                "overall": [
                    {
                        "$group": {
                            "_id": None,
                            "totalInvocations": {"$sum": 1},
                            "avgLatencyMs": {"$avg": "$latencyMs"},
                            "totalMemoriesUsed": {"$sum": "$memoriesUsed"},
                        }
                    },
                ],
                "recentActivity": [
                    {"$sort": {"timestamp": -1}},
                    {"$limit": 20},
                    {
                        "$project": {
                            "_id": 0,
                            "agentId": 1,
                            "latencyMs": 1,
                            "memoriesUsed": 1,
                            "decision": 1,
                            "success": 1,
                            "timestamp": 1,
                        }
                    },
                ],
            }
        }
    ]

    try:
        result = await db.agent_metrics.aggregate(pipeline).to_list(1)
        data = result[0] if result else {}
    except Exception:
        # $percentile may not be available on older versions — fallback
        pipeline[0]["$facet"]["perAgent"][0]["$group"].pop("p95LatencyMs", None)
        result = await db.agent_metrics.aggregate(pipeline).to_list(1)
        data = result[0] if result else {}

    return {
        "perAgent": [serialize_doc(d) for d in data.get("perAgent", [])],
        "overall": serialize_doc(data.get("overall", [{}])[0])
        if data.get("overall")
        else {},
        "recentActivity": [serialize_doc(d) for d in data.get("recentActivity", [])],
    }
