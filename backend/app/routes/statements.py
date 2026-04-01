from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.database import get_database
from app.utils.helpers import serialize_doc

router = APIRouter()


@router.get("/")
async def list_statements(
    account_iban: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    db = get_database()
    query = {}
    if account_iban:
        query["accountIban"] = account_iban

    skip = (page - 1) * limit
    cursor = db.statements.find(query).sort("statementDate", -1).skip(skip).limit(limit)
    items = [serialize_doc(doc) async for doc in cursor]
    total = await db.statements.count_documents(query)
    return {"data": items, "total": total, "page": page, "limit": limit}


@router.get("/{statement_id}")
async def get_statement(statement_id: str):
    """
    MongoDB VALUE PROP: Related Data Retrieval
    Statement header + all entries in two simple queries.
    No complex multi-table JOINs.
    """
    db = get_database()
    statement = await db.statements.find_one({"statementId": statement_id})
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")

    entries_cursor = db.statement_entries.find({"statementId": statement_id}).sort(
        "bookingDate", -1
    )
    entries = [serialize_doc(doc) async for doc in entries_cursor]

    result = serialize_doc(statement)
    result["entries"] = entries
    return result


@router.get("/{statement_id}/entries")
async def get_statement_entries(
    statement_id: str,
    credit_debit: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
):
    db = get_database()
    query = {"statementId": statement_id}
    if credit_debit:
        query["creditDebit"] = credit_debit

    skip = (page - 1) * limit
    cursor = (
        db.statement_entries.find(query).sort("bookingDate", -1).skip(skip).limit(limit)
    )
    entries = [serialize_doc(doc) async for doc in cursor]
    total = await db.statement_entries.count_documents(query)
    return {"data": entries, "total": total, "page": page, "limit": limit}
