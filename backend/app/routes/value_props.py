from fastapi import APIRouter
from datetime import datetime, timezone

from app.database import get_database
from app.utils.helpers import serialize_doc, to_decimal128

router = APIRouter()


@router.get("/document-model")
async def demo_document_model():
    """
    Demonstrates how MongoDB's document model eliminates JOINs.
    In RDBMS, a single payment would span 10+ tables.
    """
    db = get_database()
    sample = await db.payments.find_one({"status": "ACSC"})
    if not sample:
        sample = await db.payments.find_one()

    relational_tables = [
        "payments",
        "payment_parties",
        "party_addresses",
        "party_accounts",
        "payment_agents",
        "payment_charges",
        "payment_status_log",
        "payment_remittance",
        "payment_amounts",
        "settlement_info",
    ]

    return {
        "title": "Document Model - Zero JOINs",
        "description": "A single payment document contains ALL related data: "
        "parties, agents, charges, status history, remittance summary. "
        "In a relational database, this would require JOINs across 10+ tables.",
        "relationalTablesNeeded": relational_tables,
        "mongodbCollections": 1,
        "sampleDocument": serialize_doc(sample) if sample else None,
        "mongoQuery": 'db.payments.findOne({ uetr: "..." })',
        "equivalentSQL": """
            SELECT p.*, dp.name as debtor_name, da.iban as debtor_iban,
                   cp.name as creditor_name, ca.iban as creditor_iban,
                   dag.bic as debtor_agent, cag.bic as creditor_agent,
                   ch.amount as charge_amount, sl.status, sl.timestamp
            FROM payments p
            JOIN payment_parties dp ON p.debtor_id = dp.id
            JOIN party_accounts da ON dp.account_id = da.id
            JOIN party_addresses daddr ON dp.address_id = daddr.id
            JOIN payment_parties cp ON p.creditor_id = cp.id
            JOIN party_accounts ca ON cp.account_id = ca.id
            JOIN payment_agents dag ON p.debtor_agent_id = dag.id
            JOIN payment_agents cag ON p.creditor_agent_id = cag.id
            LEFT JOIN payment_charges ch ON p.id = ch.payment_id
            LEFT JOIN payment_status_log sl ON p.id = sl.payment_id
            ORDER BY sl.timestamp DESC
        """,
    }


@router.get("/flexible-schema")
async def demo_flexible_schema():
    """
    Demonstrates MongoDB's flexible schema for polymorphic ISO 20022 messages.
    """
    db = get_database()

    # Different message types have different fields
    pacs008 = await db.payments.find_one({"messageType": "pacs.008"})
    pacs004 = await db.payments.find_one({"messageType": "pacs.004"})

    return {
        "title": "Flexible Schema - Polymorphic Messages",
        "description": "ISO 20022 has 775+ message types with different structures. "
        "MongoDB stores them all without ALTER TABLE. "
        "pacs.008 (credit transfer) and pacs.004 (return) have different fields "
        "but coexist in the same collection.",
        "benefit": "No schema migrations, no ALTER TABLE downtime, no NULL columns. "
        "Each document carries exactly the fields it needs.",
        "pacs008Sample": serialize_doc(pacs008)
        if pacs008
        else "No pacs.008 sample available",
        "pacs004Sample": serialize_doc(pacs004)
        if pacs004
        else "No pacs.004 sample available",
    }


@router.get("/aggregation-power")
async def demo_aggregation_power():
    """
    Demonstrates MongoDB aggregation framework for real-time analytics.
    """
    db = get_database()

    pipeline = [
        {
            "$facet": {
                "byStatus": [
                    {
                        "$group": {
                            "_id": "$status",
                            "count": {"$sum": 1},
                            "volume": {"$sum": {"$toDouble": "$settlementAmount"}},
                        }
                    },
                    {"$sort": {"volume": -1}},
                ],
                "byCurrency": [
                    {
                        "$group": {
                            "_id": "$settlementCurrency",
                            "count": {"$sum": 1},
                            "volume": {"$sum": {"$toDouble": "$settlementAmount"}},
                        }
                    },
                    {"$sort": {"volume": -1}},
                ],
                "byCountryCorridor": [
                    {
                        "$group": {
                            "_id": {
                                "from": "$debtor.address.country",
                                "to": "$creditor.address.country",
                            },
                            "count": {"$sum": 1},
                            "volume": {"$sum": {"$toDouble": "$settlementAmount"}},
                        }
                    },
                    {"$sort": {"volume": -1}},
                    {"$limit": 5},
                ],
                "totalStats": [
                    {
                        "$group": {
                            "_id": None,
                            "total": {"$sum": 1},
                            "totalVolume": {"$sum": {"$toDouble": "$settlementAmount"}},
                            "avgAmount": {"$avg": {"$toDouble": "$settlementAmount"}},
                        }
                    },
                ],
            }
        }
    ]

    result = await db.payments.aggregate(pipeline).to_list(1)

    return {
        "title": "Aggregation Framework - Server-Side Analytics",
        "description": "MongoDB's aggregation pipeline computes complex analytics "
        "entirely server-side. $facet runs multiple aggregations "
        "in a single pass over the data.",
        "benefit": "No data movement to app layer. Real-time analytics on live data. "
        "Single pipeline replaces multiple SQL queries with GROUP BY.",
        "pipeline": "$facet with 4 parallel aggregations",
        "results": result[0] if result else {},
    }


@router.get("/schema-validation")
async def demo_schema_validation():
    """
    Demonstrates MongoDB schema validation for data quality enforcement.
    """
    db = get_database()

    # Get current validator
    try:
        coll_info = await db.command("listCollections", filter={"name": "payments"})
        collections = coll_info.get("cursor", {}).get("firstBatch", [])
        validator = (
            collections[0].get("options", {}).get("validator") if collections else None
        )
    except Exception:
        validator = "Schema validation is configured"

    return {
        "title": "Schema Validation - Data Quality at DB Level",
        "description": "MongoDB enforces ISO 20022 data quality rules at the database level: "
        "UETR must be UUID v4, currency must be 3-letter ISO 4217, "
        "status must be a valid ISO 20022 code, amounts must be Decimal128.",
        "benefit": "Data quality enforced regardless of which application writes data. "
        "validationLevel: 'moderate' allows gradual migration. "
        "validationAction: 'warn' logs violations without rejecting writes.",
        "validator": validator,
        "validatedFields": {
            "uetr": "UUID v4 pattern regex",
            "settlementCurrency": "^[A-Z]{3}$ (ISO 4217)",
            "status": "enum: ACTC, ACCP, ACSP, ACSC, RJCT, PDNG, CANC",
            "settlementAmount": "bsonType: decimal (Decimal128)",
            "statusHistory": "maxItems: 50",
            "charges": "maxItems: 20",
        },
    }


@router.get("/atomic-operations")
async def demo_atomic_operations():
    """
    Demonstrates MongoDB's atomic operations on rich documents.
    """
    return {
        "title": "Atomic Operations - No Distributed Transactions Needed",
        "description": "MongoDB updates the payment status AND appends to status history "
        "in a single atomic operation. No BEGIN/COMMIT/ROLLBACK needed.",
        "benefit": "Eliminates race conditions. No partial updates. "
        "Single document updates are always atomic in MongoDB.",
        "exampleOperation": {
            "operation": "Update payment status",
            "mongoCommand": """
                db.payments.updateOne(
                    { uetr: "eb6305c9-..." },
                    {
                        $set: { status: "ACSC", statusReason: null },
                        $push: { statusHistory: { status: "ACSC", timestamp: ISODate(), reason: null } }
                    }
                )
            """,
            "equivalentSQL": """
                BEGIN TRANSACTION;
                UPDATE payments SET status = 'ACSC' WHERE uetr = '...';
                INSERT INTO payment_status_log (payment_id, status, timestamp) VALUES (...);
                COMMIT;
            """,
        },
    }


@router.get("/decimal128-precision")
async def demo_decimal_precision():
    """
    Demonstrates Decimal128 for financial precision.
    """
    db = get_database()

    # Show a real payment with Decimal128 amounts
    sample = await db.payments.find_one({"settlementAmount": {"$exists": True}})

    return {
        "title": "Decimal128 - Financial-Grade Precision",
        "description": "MongoDB natively supports Decimal128 (IEEE 754-2008) for exact "
        "monetary arithmetic. No floating-point rounding errors.",
        "benefit": "0.1 + 0.2 = 0.3 (not 0.30000000000000004). "
        "34 significant digits. Range: ±9.999...×10^6144. "
        "Critical for cross-currency settlement calculations.",
        "example": {
            "floatingPoint": "0.1 + 0.2 = 0.30000000000000004 (WRONG)",
            "decimal128": "Decimal128('0.1') + Decimal128('0.2') = Decimal128('0.3') (CORRECT)",
        },
        "samplePayment": {
            "amount": str(sample.get("settlementAmount")) if sample else "10000.00",
            "type": "Decimal128",
        }
        if sample
        else None,
    }


@router.get("/ttl-indexes")
async def demo_ttl_indexes():
    """
    Demonstrates TTL indexes for automatic data lifecycle management.
    """
    return {
        "title": "TTL Indexes - Automatic Data Lifecycle",
        "description": "MongoDB automatically expires data using TTL (Time-To-Live) indexes. "
        "Status reports expire after 1 year. Notifications expire after 90 days.",
        "benefit": "No cron jobs. No manual cleanup. Data lifecycle managed by the database engine. "
        "Different collections can have different retention policies.",
        "collections": {
            "status_reports": {
                "ttl": "1 year (31,536,000 seconds)",
                "reason": "Short-term operational data",
            },
            "notifications": {
                "ttl": "90 days (7,776,000 seconds)",
                "reason": "Real-time alerts, consumed quickly",
            },
            "payments": {
                "ttl": "None (archived manually after 7 years)",
                "reason": "Regulatory retention",
            },
            "original_messages": {
                "ttl": "None (7+ years regulatory)",
                "reason": "Compliance audit trail",
            },
        },
    }


@router.get("/summary")
async def value_props_summary():
    """Full summary of MongoDB value propositions for ISO 20022."""
    return {
        "title": "MongoDB Value Propositions for ISO 20022 Payments",
        "valuePropositions": [
            {
                "name": "Document Model",
                "icon": "FileText",
                "summary": "Store complete ISO 20022 messages as single documents. "
                "Eliminates 10+ table JOINs per payment query.",
                "endpoint": "/api/value-props/document-model",
            },
            {
                "name": "Flexible Schema",
                "icon": "Layers",
                "summary": "Handle 775+ ISO 20022 message types without schema migrations. "
                "Polymorphic collections with per-document structure.",
                "endpoint": "/api/value-props/flexible-schema",
            },
            {
                "name": "Aggregation Framework",
                "icon": "BarChart3",
                "summary": "Real-time payment analytics computed server-side. "
                "$facet for parallel aggregations in single pipeline.",
                "endpoint": "/api/value-props/aggregation-power",
            },
            {
                "name": "Schema Validation",
                "icon": "ShieldCheck",
                "summary": "Enforce ISO 20022 data quality (UETR format, currency codes, "
                "status enums) at the database level.",
                "endpoint": "/api/value-props/schema-validation",
            },
            {
                "name": "Atomic Operations",
                "icon": "Zap",
                "summary": "Update status + append history atomically. "
                "No distributed transactions for single-document updates.",
                "endpoint": "/api/value-props/atomic-operations",
            },
            {
                "name": "Decimal128 Precision",
                "icon": "Calculator",
                "summary": "Financial-grade decimal arithmetic. "
                "No floating-point rounding errors in monetary calculations.",
                "endpoint": "/api/value-props/decimal128-precision",
            },
            {
                "name": "TTL Indexes",
                "icon": "Clock",
                "summary": "Automatic data lifecycle management. "
                "Notifications expire in 90 days, status reports in 1 year.",
                "endpoint": "/api/value-props/ttl-indexes",
            },
        ],
    }
