from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.database import get_database
from app.utils.helpers import serialize_doc, generate_message_id, now_utc

router = APIRouter()


@router.get("/")
async def list_investigations(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    db = get_database()
    query = {}
    if status:
        query["status"] = status

    skip = (page - 1) * limit
    cursor = db.investigations.find(query).sort("createdAt", -1).skip(skip).limit(limit)
    items = [serialize_doc(doc) async for doc in cursor]
    total = await db.investigations.count_documents(query)
    return {"data": items, "total": total, "page": page, "limit": limit}


@router.get("/{case_id}")
async def get_investigation(case_id: str):
    db = get_database()
    investigation = await db.investigations.find_one({"caseId": case_id})
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return serialize_doc(investigation)


@router.post("/")
async def create_investigation(data: dict):
    """
    MongoDB VALUE PROP: Embedded Message Chain
    The investigation document contains the full correspondence chain
    embedded as an array. No separate join table needed.
    """
    db = get_database()
    now = now_utc()
    case_id = generate_message_id("INV")
    msg_id = generate_message_id(f"CAMT{data.get('type', '056').replace('camt.', '')}")

    investigation = {
        "caseId": case_id,
        "messageId": msg_id,
        "messageType": data.get("type", "camt.056"),
        "createdAt": now,
        "originalUetr": data.get("originalUetr"),
        "originalEndToEndId": data.get("originalEndToEndId"),
        "originalMessageId": data.get("originalMessageId"),
        "originalMessageType": data.get("originalMessageType", "pacs.008"),
        "originalAmount": None,
        "originalCurrency": None,
        "reason": data.get("reason", ""),
        "reasonDescription": data.get("reasonDescription", ""),
        "requestedAction": data.get("requestedAction", "cancellation"),
        "initiator": data.get("initiator", {}),
        "respondent": data.get("respondent", {}),
        "status": "OPEN",
        "resolution": None,
        "resolvedAt": None,
        "resolutionDetails": None,
        "messages": [
            {
                "messageId": msg_id,
                "messageType": data.get("type", "camt.056"),
                "direction": "outbound",
                "timestamp": now,
                "summary": data.get("summary", "Investigation initiated"),
            }
        ],
    }

    await db.investigations.insert_one(investigation)
    return {"caseId": case_id, "status": "OPEN"}


@router.put("/{case_id}/resolve")
async def resolve_investigation(case_id: str, data: dict):
    """
    MongoDB VALUE PROP: Atomic Update with Array Push
    Resolve and append resolution message atomically.
    """
    db = get_database()
    now = now_utc()

    result = await db.investigations.update_one(
        {"caseId": case_id},
        {
            "$set": {
                "status": "RESOLVED",
                "resolution": data.get("resolution", "ACCP"),
                "resolvedAt": now,
                "resolutionDetails": data.get("details", ""),
            },
            "$push": {
                "messages": {
                    "messageId": generate_message_id("CAMT029"),
                    "messageType": "camt.029",
                    "direction": "inbound",
                    "timestamp": now,
                    "summary": data.get("details", "Investigation resolved"),
                }
            },
        },
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Investigation not found")

    return {"caseId": case_id, "status": "RESOLVED"}
