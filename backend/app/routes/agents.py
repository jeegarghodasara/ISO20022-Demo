"""
Agent API routes — orchestrate multi-agent payment analysis.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.database import get_database
from app.utils.helpers import serialize_doc
from app.agents.specialists import (
    AGENT_REGISTRY,
    orchestrator_process,
    routing_agent_process,
    compliance_agent_process,
    exception_agent_process,
    reconciliation_agent_process,
)
from app.agents.memory import get_agent_memories, get_memory_stats, recall_memories
from app.agents.message_bus import get_conversation_messages, get_recent_messages

router = APIRouter()

AGENT_HANDLERS = {
    "routing-agent": routing_agent_process,
    "compliance-agent": compliance_agent_process,
    "exception-agent": exception_agent_process,
    "reconciliation-agent": reconciliation_agent_process,
    "orchestrator": orchestrator_process,
}


@router.get("/")
async def list_agents():
    """List all agents with their status and memory counts."""
    db = get_database()

    agents = []
    for agent_id, info in AGENT_REGISTRY.items():
        memory_count = await db.agent_memory.count_documents({"agentId": agent_id})
        message_count = await db.agent_messages.count_documents(
            {"$or": [{"fromAgent": agent_id}, {"toAgent": agent_id}]}
        )
        agents.append(
            {
                "agentId": agent_id,
                **info,
                "memoryCount": memory_count,
                "messageCount": message_count,
            }
        )

    return {"agents": agents}


@router.post("/ask")
async def ask_agent(body: dict):
    """
    Ask an agent (or the orchestrator) to analyze a payment.

    MongoDB VALUE PROP: Multi-Agent Architecture powered entirely by MongoDB.
    - Vector Search for semantic memory retrieval
    - Aggregation pipelines for real-time pattern analysis
    - Change Streams for inter-agent communication
    - Polymorphic collections for different memory types
    - TTL indexes for memory decay
    """
    question = body.get("question", "").strip()
    uetr = body.get("uetr", "").strip()
    agent_id = body.get("agentId", "orchestrator")

    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    # Fetch the payment if UETR provided
    payment = {}
    if uetr:
        db = get_database()
        doc = await db.payments.find_one({"uetr": uetr})
        if doc:
            payment = serialize_doc(doc)
            # Remove large fields
            payment.pop("embedding", None)
            payment.pop("remittanceEmbedding", None)
        else:
            raise HTTPException(status_code=404, detail="Payment not found")

    # Create a conversation
    conversation_id = str(uuid.uuid4())

    # Store conversation
    db = get_database()
    await db.agent_conversations.insert_one(
        {
            "conversationId": conversation_id,
            "question": question,
            "uetr": uetr,
            "agentId": agent_id,
            "createdAt": datetime.now(timezone.utc),
        }
    )

    # Route to the right agent
    handler = AGENT_HANDLERS.get(agent_id)
    if not handler:
        raise HTTPException(status_code=400, detail=f"Unknown agent: {agent_id}")

    result = await handler(payment, question, conversation_id)

    return {
        "conversationId": conversation_id,
        "question": question,
        "uetr": uetr,
        "result": result,
    }


@router.get("/memory/{agent_id}")
async def get_memories(agent_id: str, memory_type: str = None, limit: int = 20):
    """Get an agent's memories (for the memory inspector)."""
    if agent_id not in AGENT_REGISTRY:
        raise HTTPException(status_code=404, detail="Agent not found")

    memories = await get_agent_memories(agent_id, memory_type, limit)
    return {"agentId": agent_id, "memories": memories, "total": len(memories)}


@router.get("/memory-stats")
async def memory_stats():
    """Get memory statistics across all agents."""
    stats = await get_memory_stats()
    return {"stats": stats}


@router.get("/messages")
async def recent_messages(limit: int = 50):
    """Get recent inter-agent messages."""
    messages = await get_recent_messages(limit)
    return {"messages": messages, "total": len(messages)}


@router.get("/conversations")
async def list_conversations(limit: int = 20):
    """List recent agent conversations."""
    db = get_database()
    cursor = (
        db.agent_conversations.find({}, {"_id": 0}).sort("createdAt", -1).limit(limit)
    )
    conversations = [serialize_doc(doc) async for doc in cursor]
    return {"conversations": conversations}
