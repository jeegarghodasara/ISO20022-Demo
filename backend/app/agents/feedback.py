"""
User Feedback — thumbs up/down on agent responses.

MongoDB VALUE PROP: Atomic $set on nested fields.
Feedback is stored on the conversation turn document, not in a separate table.
Aggregation computes approval rates per agent server-side.
"""

from datetime import datetime, timezone

from app.database import get_database
from app.utils.helpers import serialize_doc


async def submit_feedback(
    conversation_id: str,
    turn_number: int,
    feedback: str,  # "up" or "down"
    comment: str = None,
) -> bool:
    """Store feedback on a specific conversation turn."""
    db = get_database()
    now = datetime.now(timezone.utc)

    # Find the conversation and update the specific turn
    result = await db.agent_conversations.update_one(
        {
            "conversationId": conversation_id,
            "turns.turnNumber": turn_number,
        },
        {
            "$set": {
                "turns.$.feedback": {
                    "rating": feedback,
                    "comment": comment,
                    "timestamp": now,
                }
            }
        },
    )
    return result.modified_count > 0


async def get_feedback_stats() -> dict:
    """
    Compute feedback statistics per agent.

    MongoDB VALUE PROP: Aggregation on nested arrays.
    $unwind the turns array, then $group by agent to compute approval rates.
    """
    db = get_database()

    pipeline = [
        {"$unwind": "$turns"},
        {"$match": {"turns.feedback": {"$exists": True}}},
        {
            "$group": {
                "_id": "$turns.agentId",
                "totalFeedback": {"$sum": 1},
                "thumbsUp": {
                    "$sum": {"$cond": [{"$eq": ["$turns.feedback.rating", "up"]}, 1, 0]}
                },
                "thumbsDown": {
                    "$sum": {
                        "$cond": [{"$eq": ["$turns.feedback.rating", "down"]}, 1, 0]
                    }
                },
            }
        },
        {
            "$addFields": {
                "approvalRate": {
                    "$cond": [
                        {"$gt": ["$totalFeedback", 0]},
                        {"$divide": ["$thumbsUp", "$totalFeedback"]},
                        0,
                    ]
                }
            }
        },
        {"$sort": {"totalFeedback": -1}},
    ]

    cursor = db.agent_conversations.aggregate(pipeline)
    stats = [serialize_doc(doc) async for doc in cursor]
    return stats
