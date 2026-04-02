"""
Agent API routes — orchestrate multi-agent payment analysis.

Conversations are multi-turn, stored as a single MongoDB document with a
turns[] array. Each turn contains the question and the full agent result.
When a conversation exceeds 10KB, the backend signals the frontend to
start a new conversation — similar to how ChatGPT handles context limits.

MongoDB VALUE PROP: Growing documents with atomic $push, $set, and $inc
in a single update. The entire multi-turn conversation is one document —
no JOINs across conversations + turns + results tables.
"""

import json
import sys
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
from app.agents.metrics import get_agent_metrics_summary
from app.agents.feedback import submit_feedback, get_feedback_stats
from app.agents.tool_logger import get_tool_logs, get_tool_stats
from app.agents.consolidation import run_full_consolidation

router = APIRouter()

AGENT_HANDLERS = {
    "routing-agent": routing_agent_process,
    "compliance-agent": compliance_agent_process,
    "exception-agent": exception_agent_process,
    "reconciliation-agent": reconciliation_agent_process,
    "orchestrator": orchestrator_process,
}

# Max conversation size in bytes (10KB)
MAX_CONVERSATION_BYTES = 10 * 1024


def _estimate_doc_size(doc: dict) -> int:
    """Estimate BSON document size using JSON serialization as proxy."""
    try:
        return len(json.dumps(doc, default=str).encode("utf-8"))
    except Exception:
        return 0


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
    Ask an agent within a multi-turn conversation.

    If conversationId is provided, appends to the existing conversation.
    If the conversation exceeds 10KB, returns conversationFull=true
    so the frontend can prompt the user to start a new conversation.

    MongoDB VALUE PROP: Multi-Turn Conversations as Growing Documents
    - Atomic $push to append turns to the conversation
    - $inc to track sizeBytes
    - $set to update metadata
    - One document = one complete conversation with full context
    """
    question = body.get("question", "").strip()
    uetr = body.get("uetr", "").strip()
    agent_id = body.get("agentId", "orchestrator")
    conversation_id = body.get("conversationId", "").strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    db = get_database()

    # Fetch the payment if UETR provided
    payment = {}
    if uetr:
        doc = await db.payments.find_one({"uetr": uetr})
        if doc:
            payment = serialize_doc(doc)
            payment.pop("embedding", None)
            payment.pop("remittanceEmbedding", None)
        else:
            raise HTTPException(status_code=404, detail="Payment not found")

    # Route to the right agent
    handler = AGENT_HANDLERS.get(agent_id)
    if not handler:
        raise HTTPException(status_code=400, detail=f"Unknown agent: {agent_id}")

    # Build context from prior turns if continuing a conversation
    prior_context = []
    existing_conv = None
    if conversation_id:
        existing_conv = await db.agent_conversations.find_one(
            {"conversationId": conversation_id}
        )
        if existing_conv:
            # Check if conversation is already full
            current_size = existing_conv.get("sizeBytes", 0)
            if current_size >= MAX_CONVERSATION_BYTES:
                return {
                    "conversationId": conversation_id,
                    "conversationFull": True,
                    "sizeBytes": current_size,
                    "maxBytes": MAX_CONVERSATION_BYTES,
                    "message": "Conversation has reached the 10KB limit. Please start a new conversation.",
                    "turnCount": len(existing_conv.get("turns", [])),
                }
            # Extract prior Q&A for context
            for turn in existing_conv.get("turns", []):
                prior_context.append(
                    {
                        "question": turn.get("question", ""),
                        "decision": turn.get("result", {}).get("decision", ""),
                    }
                )

    # If no conversation_id, create a new one
    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    # Build enriched question with prior context
    enriched_question = question
    if prior_context:
        context_summary = "; ".join(
            f"Q: {c['question']} -> A: {c['decision']}" for c in prior_context[-5:]
        )
        enriched_question = (
            f"[Prior context: {context_summary}] Current question: {question}"
        )

    # Execute the agent
    result = await handler(payment, enriched_question, conversation_id)

    # Build the turn
    now = datetime.now(timezone.utc)
    turn = {
        "turnNumber": len(prior_context) + 1,
        "question": question,
        "uetr": uetr,
        "agentId": agent_id,
        "result": result,
        "timestamp": now,
    }
    turn_size = _estimate_doc_size(turn)

    if existing_conv:
        # Append turn to existing conversation
        new_size = existing_conv.get("sizeBytes", 0) + turn_size
        await db.agent_conversations.update_one(
            {"conversationId": conversation_id},
            {
                "$push": {"turns": turn},
                "$set": {"updatedAt": now, "lastQuestion": question},
                "$inc": {"sizeBytes": turn_size},
            },
        )
        total_turns = len(existing_conv.get("turns", [])) + 1
    else:
        # Create new conversation document
        new_size = turn_size + 200  # overhead for metadata fields
        conversation = {
            "conversationId": conversation_id,
            "turns": [turn],
            "sizeBytes": new_size,
            "createdAt": now,
            "updatedAt": now,
            "lastQuestion": question,
        }
        await db.agent_conversations.insert_one(conversation)
        total_turns = 1

    # Check if conversation is now approaching the limit
    conversation_full = new_size >= MAX_CONVERSATION_BYTES
    approaching_limit = new_size >= MAX_CONVERSATION_BYTES * 0.8

    return {
        "conversationId": conversation_id,
        "question": question,
        "uetr": uetr,
        "result": result,
        "turnNumber": total_turns,
        "sizeBytes": new_size,
        "maxBytes": MAX_CONVERSATION_BYTES,
        "conversationFull": conversation_full,
        "approachingLimit": approaching_limit,
        "priorTurns": len(prior_context),
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
    """
    List recent multi-turn conversations with full turn history.

    MongoDB VALUE PROP: Document Model for Conversations
    Each conversation is a single document containing all turns, results,
    and metadata. One read returns the complete conversation — no JOINs
    across conversations + turns + results tables.
    """
    db = get_database()
    cursor = (
        db.agent_conversations.find({}, {"_id": 0}).sort("updatedAt", -1).limit(limit)
    )
    conversations = [serialize_doc(doc) async for doc in cursor]
    return {"conversations": conversations, "total": len(conversations)}


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a single conversation with all turns."""
    db = get_database()
    conv = await db.agent_conversations.find_one(
        {"conversationId": conversation_id}, {"_id": 0}
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return serialize_doc(conv)


# ============================================================================
# Feature 2: Agent Performance Metrics
# ============================================================================


@router.get("/metrics")
async def agent_metrics():
    """
    Agent performance metrics — latency, invocation counts, memory usage.

    MongoDB VALUE PROP: $facet aggregation computes per-agent stats,
    overall stats, and recent activity in a single pipeline pass.
    """
    return await get_agent_metrics_summary()


# ============================================================================
# Feature 3: User Feedback
# ============================================================================


@router.post("/feedback")
async def post_feedback(body: dict):
    """
    Submit thumbs up/down feedback on an agent response.

    MongoDB VALUE PROP: Atomic $set on nested array element.
    Updates a specific turn inside the conversation document.
    """
    conversation_id = body.get("conversationId", "")
    turn_number = body.get("turnNumber", 0)
    rating = body.get("rating", "")  # "up" or "down"
    comment = body.get("comment")

    if not conversation_id or not turn_number or rating not in ("up", "down"):
        raise HTTPException(
            status_code=400,
            detail="conversationId, turnNumber, and rating (up/down) required",
        )

    success = await submit_feedback(conversation_id, turn_number, rating, comment)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation or turn not found")

    return {
        "status": "ok",
        "conversationId": conversation_id,
        "turnNumber": turn_number,
        "rating": rating,
    }


@router.get("/feedback-stats")
async def feedback_statistics():
    """
    Feedback statistics per agent — approval rates via $unwind + $group.

    MongoDB VALUE PROP: Aggregation on nested arrays without denormalization.
    """
    stats = await get_feedback_stats()
    return {"stats": stats}


# ============================================================================
# Feature 4: Tool Call Logging
# ============================================================================


@router.get("/tool-logs")
async def tool_logs(agent_id: str = None, limit: int = 50):
    """
    Audit trail of every DB operation agents executed.

    MongoDB VALUE PROP: Append-only audit log with TTL (30-day retention).
    """
    logs = await get_tool_logs(agent_id, limit)
    return {"logs": logs, "total": len(logs)}


@router.get("/tool-stats")
async def tool_statistics():
    """Tool usage statistics per agent."""
    stats = await get_tool_stats()
    return {"stats": stats}


# ============================================================================
# Feature 5: Memory Consolidation
# ============================================================================


@router.post("/consolidate")
async def consolidate_memories():
    """
    Trigger memory consolidation — distill episodic memories into semantic knowledge.

    MongoDB VALUE PROP: Aggregation for knowledge distillation.
    $group episodic memories by context patterns, compute statistics,
    and insert summarized semantic memories.
    """
    result = await run_full_consolidation()
    return result
