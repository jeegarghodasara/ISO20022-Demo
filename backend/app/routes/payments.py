from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
from bson import Decimal128

from app.database import get_database
from app.utils.helpers import (
    serialize_doc,
    generate_uetr,
    generate_message_id,
    to_decimal128,
    now_utc,
)

router = APIRouter()

# Human-readable labels for message types
MESSAGE_TYPE_LABELS = {
    "pacs.008": "Customer Credit Transfer",
    "pacs.009": "Bank-to-Bank Transfer",
    "pacs.004": "Payment Return",
    "pain.001": "Payment Initiation",
    "pain.008": "Direct Debit Initiation",
}

VALID_MESSAGE_TYPES = list(MESSAGE_TYPE_LABELS.keys())

# Message ID prefixes per type
MESSAGE_ID_PREFIXES = {
    "pacs.008": "PACS008",
    "pacs.009": "PACS009",
    "pacs.004": "PACS004",
    "pain.001": "PAIN001",
    "pain.008": "PAIN008",
}

# Message versions per type
MESSAGE_VERSIONS = {
    "pacs.008": "001.014",
    "pacs.009": "001.012",
    "pacs.004": "001.013",
    "pain.001": "001.013",
    "pain.008": "001.012",
}


@router.get("/")
async def list_payments(
    status: Optional[str] = None,
    currency: Optional[str] = None,
    message_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    debtor_iban: Optional[str] = None,
    creditor_iban: Optional[str] = None,
    agent_bic: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """
    MongoDB VALUE PROP: Flexible Querying on Polymorphic Data
    Single collection stores all payment types. Dynamic filters query across
    all types seamlessly - no UNIONs across type-specific tables needed.
    """
    db = get_database()
    query = {}

    if status:
        query["status"] = status
    if currency:
        query["settlementCurrency"] = currency
    if message_type:
        query["messageType"] = message_type
    if debtor_iban:
        query["debtor.account.iban"] = debtor_iban
    if creditor_iban:
        query["creditor.account.iban"] = creditor_iban
    if agent_bic:
        query["$or"] = [
            {"debtorAgent.bic": agent_bic},
            {"creditorAgent.bic": agent_bic},
        ]
    if date_from or date_to:
        date_filter = {}
        if date_from:
            date_filter["$gte"] = datetime.fromisoformat(date_from)
        if date_to:
            date_filter["$lte"] = datetime.fromisoformat(date_to)
        query["settlementDate"] = date_filter

    skip = (page - 1) * limit
    cursor = db.payments.find(query).sort("settlementDate", -1).skip(skip).limit(limit)
    payments = [serialize_doc(doc) async for doc in cursor]
    total = await db.payments.count_documents(query)

    return {
        "data": payments,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "messageTypeLabels": MESSAGE_TYPE_LABELS,
    }


@router.get("/search")
async def search_payments(q: str = Query(..., min_length=1)):
    """
    MongoDB VALUE PROP: Multi-field search across polymorphic documents.
    Search across UETR, EndToEndId, debtor/creditor names in a single query
    regardless of whether the document is a credit transfer, return, or direct debit.
    """
    db = get_database()
    query = {
        "$or": [
            {"uetr": {"$regex": q, "$options": "i"}},
            {"endToEndId": {"$regex": q, "$options": "i"}},
            {"debtor.name": {"$regex": q, "$options": "i"}},
            {"creditor.name": {"$regex": q, "$options": "i"}},
            {"messageId": {"$regex": q, "$options": "i"}},
        ]
    }
    cursor = db.payments.find(query).sort("createdAt", -1).limit(50)
    payments = [serialize_doc(doc) async for doc in cursor]
    return {"data": payments, "total": len(payments)}


@router.get("/types")
async def get_payment_types():
    """
    MongoDB VALUE PROP: Polymorphic Pattern
    Returns available payment types and their distribution in the collection.
    All types coexist in a single collection with type-specific fields.
    """
    db = get_database()
    pipeline = [
        {"$group": {"_id": "$messageType", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    cursor = db.payments.aggregate(pipeline)
    distribution = {doc["_id"]: doc["count"] async for doc in cursor}

    return {
        "types": [
            {
                "id": type_id,
                "label": label,
                "count": distribution.get(type_id, 0),
            }
            for type_id, label in MESSAGE_TYPE_LABELS.items()
        ],
        "total": sum(distribution.values()),
    }


@router.get("/{uetr}")
async def get_payment(uetr: str):
    """
    MongoDB VALUE PROP: Document Model with Polymorphism
    Single read returns the COMPLETE payment with type-specific fields.
    A pacs.004 return includes originalUetr and returnReason.
    A pain.001 initiation includes initiatingParty and numberOfTransactions.
    No JOINs across type-specific tables needed.
    """
    db = get_database()
    payment = await db.payments.find_one({"uetr": uetr})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Also fetch remittance details (separate collection for unbounded data)
    remittance_cursor = db.remittance_details.find({"paymentUetr": uetr})
    remittance = [serialize_doc(doc) async for doc in remittance_cursor]

    # Fetch related status reports
    status_cursor = (
        db.status_reports.find({"transactions.originalUetr": uetr})
        .sort("createdAt", -1)
        .limit(10)
    )
    status_reports = [serialize_doc(doc) async for doc in status_cursor]

    result = serialize_doc(payment)
    result["remittanceDetails"] = remittance
    result["statusReports"] = status_reports
    result["messageTypeLabel"] = MESSAGE_TYPE_LABELS.get(
        result.get("messageType"), result.get("messageType")
    )
    return result


@router.post("/")
async def create_payment(payment_data: dict):
    """
    MongoDB VALUE PROP: Polymorphic Document Model + Atomic Operations
    Insert payment documents with different structures into a single collection.
    Each message type (pacs.008, pacs.009, pacs.004, pain.001, pain.008) has its
    own specific fields while sharing common ones. MongoDB handles this naturally
    without any schema migration or ALTER TABLE statements.
    """
    db = get_database()
    message_type = payment_data.get("messageType", "pacs.008")

    if message_type not in VALID_MESSAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid message type. Must be one of: {', '.join(VALID_MESSAGE_TYPES)}",
        )

    uetr = generate_uetr()
    now = now_utc()
    prefix = MESSAGE_ID_PREFIXES.get(message_type, "PAY")
    version = MESSAGE_VERSIONS.get(message_type, "001.001")

    # --- Common fields shared by ALL payment types ---
    payment = {
        "messageId": generate_message_id(prefix),
        "messageType": message_type,
        "messageVersion": version,
        "direction": "outbound",
        "createdAt": now,
        "receivedAt": now,
        "uetr": uetr,
        "endToEndId": payment_data.get("endToEndId", generate_message_id("E2E")),
        "txId": generate_message_id("TX"),
        "instrId": generate_message_id("INSTR"),
        "settlementAmount": to_decimal128(payment_data.get("amount", 0)),
        "settlementCurrency": payment_data.get("currency", "USD"),
        "settlementDate": datetime.fromisoformat(payment_data["settlementDate"])
        if payment_data.get("settlementDate")
        else now,
        "priority": payment_data.get("priority", "NORM"),
        "status": "ACTC",
        "statusReason": None,
        "statusHistory": [{"status": "ACTC", "timestamp": now, "reason": None}],
        "debtor": payment_data.get("debtor", {}),
        "creditor": payment_data.get("creditor", {}),
        "debtorAgent": payment_data.get("debtorAgent", {}),
        "creditorAgent": payment_data.get("creditorAgent", {}),
        "charges": [],
        "remittanceSummary": {
            "type": "unstructured",
            "unstructuredText": payment_data.get("remittanceInfo", ""),
            "documentCount": 0,
            "totalRemittedAmount": to_decimal128(payment_data.get("amount", 0)),
        },
        "archivedAt": None,
    }

    # --- Type-specific fields (polymorphic part) ---
    if message_type == "pacs.008":
        # FI-to-FI Customer Credit Transfer
        payment.update(
            {
                "settlementMethod": payment_data.get("settlementMethod", "CLRG"),
                "instructedAmount": to_decimal128(
                    payment_data.get("instructedAmount", payment_data.get("amount", 0))
                ),
                "instructedCurrency": payment_data.get(
                    "instructedCurrency", payment_data.get("currency", "USD")
                ),
                "exchangeRate": to_decimal128(payment_data.get("exchangeRate", 1.0)),
                "chargeBearer": payment_data.get("chargeBearer", "SHAR"),
                "serviceLevel": payment_data.get("serviceLevel", "SEPA"),
                "purpose": payment_data.get("purpose", ""),
                "instructingAgent": payment_data.get("debtorAgent", {}),
                "instructedAgent": payment_data.get("creditorAgent", {}),
            }
        )

    elif message_type == "pacs.009":
        # FI-to-FI Financial Institution Credit Transfer (bank-to-bank)
        payment.update(
            {
                "settlementMethod": payment_data.get("settlementMethod", "CLRG"),
                "chargeBearer": payment_data.get("chargeBearer", "SHAR"),
                "serviceLevel": payment_data.get("serviceLevel", "SEPA"),
                "instructingAgent": payment_data.get(
                    "instructingAgent", payment_data.get("debtorAgent", {})
                ),
                "instructedAgent": payment_data.get(
                    "instructedAgent", payment_data.get("creditorAgent", {})
                ),
                "intermediaryAgent1": payment_data.get("intermediaryAgent1"),
            }
        )

    elif message_type == "pacs.004":
        # Payment Return
        original_uetr = payment_data.get("originalUetr")
        return_reason = payment_data.get("returnReason", {})
        payment.update(
            {
                "originalUetr": original_uetr,
                "originalMessageRef": original_uetr,
                "returnReason": {
                    "code": return_reason.get("code", "AC04"),
                    "description": return_reason.get("description", ""),
                },
                "settlementMethod": payment_data.get("settlementMethod", "CLRG"),
            }
        )
        # Look up the original payment if UETR is provided
        if original_uetr:
            original = await db.payments.find_one({"uetr": original_uetr})
            if original:
                payment["originalPaymentRef"] = {
                    "messageId": original.get("messageId"),
                    "messageType": original.get("messageType"),
                    "settlementAmount": original.get("settlementAmount"),
                    "settlementCurrency": original.get("settlementCurrency"),
                    "settlementDate": original.get("settlementDate"),
                }

    elif message_type == "pain.001":
        # Customer Credit Transfer Initiation
        payment.update(
            {
                "initiatingParty": payment_data.get("initiatingParty", {}),
                "numberOfTransactions": payment_data.get("numberOfTransactions", 1),
                "controlSum": to_decimal128(payment_data.get("amount", 0)),
                "requestedExecutionDate": datetime.fromisoformat(
                    payment_data["requestedExecutionDate"]
                )
                if payment_data.get("requestedExecutionDate")
                else now,
                "paymentMethod": "TRF",
                "serviceLevel": payment_data.get("serviceLevel", "SEPA"),
            }
        )

    elif message_type == "pain.008":
        # Customer Direct Debit Initiation
        payment.update(
            {
                "mandateId": payment_data.get("mandateId", ""),
                "creditorSchemeId": payment_data.get("creditorSchemeId", ""),
                "sequenceType": payment_data.get("sequenceType", "FRST"),
                "requestedCollectionDate": datetime.fromisoformat(
                    payment_data["requestedCollectionDate"]
                )
                if payment_data.get("requestedCollectionDate")
                else now,
                "directDebitInfo": {
                    "mandateId": payment_data.get("mandateId", ""),
                    "creditorSchemeId": payment_data.get("creditorSchemeId", ""),
                    "sequenceType": payment_data.get("sequenceType", "FRST"),
                },
            }
        )

    await db.payments.insert_one(payment)
    return {
        "uetr": uetr,
        "messageId": payment["messageId"],
        "messageType": message_type,
        "messageTypeLabel": MESSAGE_TYPE_LABELS.get(message_type),
        "status": "ACTC",
    }


@router.put("/{uetr}/status")
async def update_payment_status(uetr: str, status_data: dict):
    """
    MongoDB VALUE PROP: Atomic Array Push
    Update status and append to history atomically - no race conditions.
    Uses $set + $push in a single atomic operation.
    Works identically across all payment types in the polymorphic collection.
    """
    db = get_database()
    new_status = status_data.get("status")
    reason = status_data.get("reason")

    if new_status not in ["ACTC", "ACCP", "ACSP", "ACSC", "RJCT", "PDNG", "CANC"]:
        raise HTTPException(status_code=400, detail="Invalid status code")

    result = await db.payments.update_one(
        {"uetr": uetr},
        {
            "$set": {
                "status": new_status,
                "statusReason": reason,
            },
            "$push": {
                "statusHistory": {
                    "status": new_status,
                    "timestamp": now_utc(),
                    "reason": reason,
                }
            },
        },
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {"uetr": uetr, "status": new_status}


@router.get("/{uetr}/trace")
async def trace_payment(uetr: str):
    """
    MongoDB VALUE PROP: Rich Document + Embedded Status History
    Full payment trace with complete status history embedded in one document.
    In relational DB this would require JOINs across payments, status_log,
    agents, parties tables - multiplied for each payment type.
    """
    db = get_database()
    payment = await db.payments.find_one({"uetr": uetr})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    result = serialize_doc(payment)
    result["messageTypeLabel"] = MESSAGE_TYPE_LABELS.get(
        result.get("messageType"), result.get("messageType")
    )
    result["trace"] = {
        "uetr": result["uetr"],
        "currentStatus": result["status"],
        "hops": [
            {
                "agent": result.get("debtorAgent", {}).get("bic", "Unknown"),
                "role": "Debtor Agent / Instructing Agent",
                "timestamp": result["createdAt"],
            },
            {
                "agent": result.get("creditorAgent", {}).get("bic", "Unknown"),
                "role": "Creditor Agent / Instructed Agent",
                "timestamp": result["statusHistory"][-1]["timestamp"]
                if result.get("statusHistory")
                else result["createdAt"],
            },
        ],
        "timeline": result.get("statusHistory", []),
    }
    return result
