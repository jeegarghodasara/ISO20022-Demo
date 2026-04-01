from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.database import get_database
from app.utils.helpers import serialize_doc, generate_message_id, now_utc

router = APIRouter()


@router.get("/")
async def list_mandates(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    db = get_database()
    query = {}
    if status:
        query["status"] = status

    skip = (page - 1) * limit
    cursor = db.mandates.find(query).sort("createdAt", -1).skip(skip).limit(limit)
    items = [serialize_doc(doc) async for doc in cursor]
    total = await db.mandates.count_documents(query)
    return {"data": items, "total": total, "page": page, "limit": limit}


@router.get("/{mandate_id}")
async def get_mandate(mandate_id: str):
    db = get_database()
    mandate = await db.mandates.find_one({"mandateId": mandate_id})
    if not mandate:
        raise HTTPException(status_code=404, detail="Mandate not found")
    return serialize_doc(mandate)
