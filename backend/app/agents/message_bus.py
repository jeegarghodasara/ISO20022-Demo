"""
Inter-Agent Message Bus — MongoDB-backed with Change Streams.

Agents communicate by inserting messages into agent_messages collection.
Each agent watches for messages addressed to it via Change Streams.
No Kafka, no RabbitMQ — MongoDB IS the message bus.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from app.database import get_database
from app.utils.helpers import serialize_doc


async def send_message(
    conversation_id: str,
    from_agent: str,
    to_agent: str,
    message_type: str,
    payload: dict,
    parent_message_id: str = None,
) -> dict:
    """Send a message from one agent to another."""
    db = get_database()
    now = datetime.now(timezone.utc)

    message = {
        "messageId": str(uuid.uuid4()),
        "conversationId": conversation_id,
        "fromAgent": from_agent,
        "toAgent": to_agent,
        "messageType": message_type,
        "payload": payload,
        "parentMessageId": parent_message_id,
        "status": "pending",
        "result": None,
        "createdAt": now,
        "completedAt": None,
        "processingTimeMs": None,
    }

    await db.agent_messages.insert_one(message)
    return serialize_doc(message)


async def complete_message(
    message_id: str,
    result: dict,
    status: str = "completed",
) -> None:
    """Mark a message as completed with a result."""
    db = get_database()
    now = datetime.now(timezone.utc)

    await db.agent_messages.update_one(
        {"messageId": message_id},
        {
            "$set": {
                "status": status,
                "result": result,
                "completedAt": now,
            }
        },
    )


async def get_conversation_messages(conversation_id: str) -> list:
    """Get all messages in a conversation."""
    db = get_database()
    cursor = db.agent_messages.find({"conversationId": conversation_id}).sort(
        "createdAt", 1
    )
    return [serialize_doc(doc) async for doc in cursor]


async def get_recent_messages(limit: int = 50) -> list:
    """Get recent agent messages across all conversations."""
    db = get_database()
    cursor = db.agent_messages.find({}, {"_id": 0}).sort("createdAt", -1).limit(limit)
    return [serialize_doc(doc) async for doc in cursor]
