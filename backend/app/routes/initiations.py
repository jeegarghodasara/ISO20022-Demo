from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime

from app.database import get_database
from app.utils.helpers import (
    serialize_doc,
    generate_uetr,
    generate_message_id,
    to_decimal128,
    now_utc,
)

router = APIRouter()


@router.get("/")
async def list_initiations(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    db = get_database()
    query = {}
    if status:
        query["status"] = status

    skip = (page - 1) * limit
    cursor = (
        db.payment_initiations.find(query).sort("createdAt", -1).skip(skip).limit(limit)
    )
    items = [serialize_doc(doc) async for doc in cursor]
    total = await db.payment_initiations.count_documents(query)
    return {"data": items, "total": total, "page": page, "limit": limit}


@router.post("/")
async def create_initiation(data: dict):
    """
    MongoDB VALUE PROP: Batch Processing with Document Model
    A pain.001 batch with 50 payments is stored as one document.
    Each individual payment is exploded into the payments collection.
    """
    db = get_database()
    now = now_utc()
    msg_id = generate_message_id("PAIN001")

    transactions = data.get("transactions", [])
    generated_uetrs = []

    # Create individual payments for each transaction
    for i, tx in enumerate(transactions):
        uetr = generate_uetr()
        generated_uetrs.append(uetr)
        payment = {
            "messageId": generate_message_id("PACS008"),
            "messageType": "pacs.008",
            "messageVersion": "001.014",
            "direction": "outbound",
            "createdAt": now,
            "receivedAt": now,
            "uetr": uetr,
            "endToEndId": tx.get("endToEndId", generate_message_id("E2E")),
            "txId": generate_message_id("TX"),
            "instrId": generate_message_id("INSTR"),
            "batchId": msg_id,
            "batchMessageId": msg_id,
            "sequenceInBatch": i + 1,
            "settlementAmount": to_decimal128(tx.get("amount", 0)),
            "settlementCurrency": tx.get("currency", data.get("currency", "USD")),
            "settlementDate": datetime.fromisoformat(data.get("executionDate"))
            if data.get("executionDate")
            else now,
            "settlementMethod": "CLRG",
            "instructedAmount": to_decimal128(tx.get("amount", 0)),
            "instructedCurrency": tx.get("currency", data.get("currency", "USD")),
            "exchangeRate": to_decimal128(1.0),
            "debtor": data.get("debtor", {}),
            "creditor": tx.get("creditor", {}),
            "debtorAgent": data.get("debtorAgent", {}),
            "creditorAgent": tx.get("creditorAgent", {}),
            "instructingAgent": data.get("debtorAgent", {}),
            "instructedAgent": tx.get("creditorAgent", {}),
            "chargeBearer": "SHAR",
            "charges": [],
            "priority": data.get("priority", "NORM"),
            "serviceLevel": data.get("serviceLevel", "SEPA"),
            "purpose": tx.get("purpose", ""),
            "status": "ACTC",
            "statusReason": None,
            "statusHistory": [{"status": "ACTC", "timestamp": now, "reason": None}],
            "remittanceSummary": {
                "type": "unstructured",
                "unstructuredText": tx.get("remittanceInfo", ""),
                "documentCount": 0,
                "totalRemittedAmount": to_decimal128(tx.get("amount", 0)),
            },
            "originalMessageRef": None,
            "archivedAt": None,
        }
        await db.payments.insert_one(payment)

    total_amount = sum(float(tx.get("amount", 0)) for tx in transactions)
    initiation = {
        "messageId": msg_id,
        "messageType": "pain.001",
        "messageVersion": "001.013",
        "createdAt": now,
        "initiatingParty": data.get("initiatingParty", {}),
        "totalTransactions": len(transactions),
        "controlSum": to_decimal128(total_amount),
        "paymentInfoId": generate_message_id("PMTINF"),
        "paymentMethod": "TRF",
        "requestedExecutionDate": datetime.fromisoformat(data.get("executionDate"))
        if data.get("executionDate")
        else now,
        "priority": data.get("priority", "NORM"),
        "serviceLevel": data.get("serviceLevel", "SEPA"),
        "debtor": data.get("debtor", {}),
        "debtorAgent": data.get("debtorAgent", {}),
        "status": "ACCP",
        "processedCount": len(transactions),
        "rejectedCount": 0,
        "generatedPaymentUetrs": generated_uetrs,
    }
    await db.payment_initiations.insert_one(initiation)

    return {
        "messageId": msg_id,
        "status": "ACCP",
        "totalTransactions": len(transactions),
        "generatedUetrs": generated_uetrs,
    }
