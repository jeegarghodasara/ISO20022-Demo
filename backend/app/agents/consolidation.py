"""
Memory Consolidation — aggregate episodic memories into semantic knowledge.

Like sleep consolidation in the human brain: after enough episodic memories
accumulate, distill them into permanent semantic knowledge.

MongoDB VALUE PROP: Aggregation pipelines for knowledge distillation.
$group episodic memories by context patterns, compute statistics,
and insert summarized semantic memories. Change Streams could trigger
this automatically when episodic memory count exceeds a threshold.
"""

from datetime import datetime, timezone

from app.database import get_database
from app.agents.memory import store_memory
from app.utils.helpers import serialize_doc


async def consolidate_routing_agent() -> dict:
    """
    Consolidate routing agent's episodic memories into semantic knowledge.

    Aggregates: corridor performance, method preferences, confidence distributions.
    """
    db = get_database()

    # Aggregate routing decisions by corridor
    pipeline = [
        {
            "$match": {
                "agentId": "routing-agent",
                "memoryType": "episodic",
                "context.corridor": {"$exists": True},
            }
        },
        {
            "$group": {
                "_id": "$context.corridor",
                "totalDecisions": {"$sum": 1},
                "methods": {"$addToSet": "$context.method"},
                "avgConfidence": {"$avg": "$context.confidence"},
                "currencies": {"$addToSet": "$context.currency"},
                "avgAmount": {"$avg": "$context.amount"},
            }
        },
        {"$match": {"totalDecisions": {"$gte": 2}}},
        {"$sort": {"totalDecisions": -1}},
    ]

    cursor = db.agent_memory.aggregate(pipeline)
    corridors = [serialize_doc(doc) async for doc in cursor]

    created = 0
    for c in corridors:
        corridor = c["_id"]
        content = (
            f"Corridor {corridor}: {c['totalDecisions']} routing decisions. "
            f"Methods used: {', '.join(c.get('methods', []))}. "
            f"Avg confidence: {c.get('avgConfidence', 0):.0%}. "
            f"Currencies: {', '.join(c.get('currencies', []))}. "
            f"Avg amount: {c.get('avgAmount', 0):,.0f}."
        )

        await store_memory(
            agent_id="routing-agent",
            memory_type="semantic",
            content=content,
            context={
                "corridor": corridor,
                "totalDecisions": c["totalDecisions"],
                "methods": c.get("methods", []),
                "avgConfidence": c.get("avgConfidence"),
                "consolidatedAt": datetime.now(timezone.utc).isoformat(),
            },
        )
        created += 1

    return {
        "agent": "routing-agent",
        "semanticMemoriesCreated": created,
        "corridorsAnalyzed": len(corridors),
    }


async def consolidate_compliance_agent() -> dict:
    """Consolidate compliance agent's episodic memories into semantic knowledge."""
    db = get_database()

    pipeline = [
        {
            "$match": {
                "agentId": "compliance-agent",
                "memoryType": "episodic",
                "context.riskLevel": {"$exists": True},
            }
        },
        {
            "$group": {
                "_id": "$context.riskLevel",
                "totalScreenings": {"$sum": 1},
                "decisions": {"$addToSet": "$context.decision"},
                "parties": {"$addToSet": "$context.debtor"},
            }
        },
        {"$sort": {"totalScreenings": -1}},
    ]

    cursor = db.agent_memory.aggregate(pipeline)
    risk_levels = [serialize_doc(doc) async for doc in cursor]

    created = 0
    for r in risk_levels:
        risk = r["_id"]
        content = (
            f"Risk level {risk}: {r['totalScreenings']} screenings. "
            f"Decisions: {', '.join(r.get('decisions', []))}. "
            f"Unique parties screened: {len(r.get('parties', []))}."
        )

        await store_memory(
            agent_id="compliance-agent",
            memory_type="semantic",
            content=content,
            context={
                "riskLevel": risk,
                "totalScreenings": r["totalScreenings"],
                "consolidatedAt": datetime.now(timezone.utc).isoformat(),
            },
        )
        created += 1

    return {"agent": "compliance-agent", "semanticMemoriesCreated": created}


async def consolidate_exception_agent() -> dict:
    """Consolidate exception agent's episodic memories into semantic knowledge."""
    db = get_database()

    pipeline = [
        {
            "$match": {
                "agentId": "exception-agent",
                "memoryType": "episodic",
                "context.reasonCode": {"$exists": True},
            }
        },
        {
            "$group": {
                "_id": "$context.reasonCode",
                "totalExceptions": {"$sum": 1},
                "statuses": {"$addToSet": "$context.status"},
            }
        },
        {"$match": {"totalExceptions": {"$gte": 2}}},
        {"$sort": {"totalExceptions": -1}},
    ]

    cursor = db.agent_memory.aggregate(pipeline)
    reasons = [serialize_doc(doc) async for doc in cursor]

    created = 0
    for r in reasons:
        code = r["_id"]
        content = (
            f"Return reason {code}: seen {r['totalExceptions']} times. "
            f"Associated statuses: {', '.join(r.get('statuses', []))}."
        )

        await store_memory(
            agent_id="exception-agent",
            memory_type="semantic",
            content=content,
            context={
                "reasonCode": code,
                "totalExceptions": r["totalExceptions"],
                "consolidatedAt": datetime.now(timezone.utc).isoformat(),
            },
        )
        created += 1

    return {"agent": "exception-agent", "semanticMemoriesCreated": created}


async def run_full_consolidation() -> dict:
    """Run memory consolidation for all agents."""
    results = {
        "routing": await consolidate_routing_agent(),
        "compliance": await consolidate_compliance_agent(),
        "exception": await consolidate_exception_agent(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    total = sum(
        r.get("semanticMemoriesCreated", 0)
        for r in results.values()
        if isinstance(r, dict)
    )
    results["totalSemanticMemoriesCreated"] = total
    return results
