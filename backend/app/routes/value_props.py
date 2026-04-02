from fastapi import APIRouter
from datetime import datetime, timezone

from app.database import get_database
from app.utils.helpers import serialize_doc, to_decimal128

router = APIRouter()


def pick_fields(doc, fields):
    """Extract a subset of fields from a document for display."""
    if not doc:
        return None
    result = {}
    for field in fields:
        parts = field.split(".")
        val = doc
        for part in parts:
            if isinstance(val, dict):
                val = val.get(part)
            else:
                val = None
                break
        if val is not None:
            # Set nested path in result
            target = result
            for part in parts[:-1]:
                if part not in target:
                    target[part] = {}
                target = target[part]
            target[parts[-1]] = val
    return result


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

    # Curated example showing the richness of a single document
    example_fields = [
        "messageType",
        "uetr",
        "endToEndId",
        "settlementAmount",
        "settlementCurrency",
        "settlementDate",
        "settlementMethod",
        "status",
        "priority",
        "debtor",
        "creditor",
        "debtorAgent",
        "creditorAgent",
        "chargeBearer",
        "charges",
        "statusHistory",
        "remittanceSummary",
    ]
    curated = pick_fields(serialize_doc(sample), example_fields) if sample else None

    return {
        "title": "Document Model - Zero JOINs",
        "description": "A single payment document contains ALL related data: "
        "parties, agents, charges, status history, remittance summary. "
        "In a relational database, this would require JOINs across 10+ tables.",
        "relationalTablesNeeded": relational_tables,
        "mongodbCollections": 1,
        "sampleDocument": curated,
        "mongoQuery": 'db.payments.findOne({ uetr: "..." })',
        "equivalentSQL": """SELECT p.*, dp.name as debtor_name, da.iban as debtor_iban,
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
ORDER BY sl.timestamp DESC""",
    }


@router.get("/flexible-schema")
async def demo_flexible_schema():
    """
    Demonstrates MongoDB's flexible schema for polymorphic ISO 20022 messages.
    Shows real documents side-by-side to highlight structural differences.
    """
    db = get_database()

    # Fetch one of each type for comparison
    pacs008 = await db.payments.find_one({"messageType": "pacs.008"})
    pacs009 = await db.payments.find_one({"messageType": "pacs.009"})
    pacs004 = await db.payments.find_one({"messageType": "pacs.004"})
    pain001 = await db.payments.find_one({"messageType": "pain.001"})
    pain008 = await db.payments.find_one({"messageType": "pain.008"})

    # Curate each to show the interesting type-specific fields
    common_fields = [
        "messageType",
        "uetr",
        "settlementAmount",
        "settlementCurrency",
        "status",
    ]
    debtor_creditor = ["debtor", "creditor"]

    def curate_sample(doc, extra_fields):
        if not doc:
            return None
        return pick_fields(
            serialize_doc(doc), common_fields + debtor_creditor + extra_fields
        )

    samples = {
        "pacs.008 - Customer Credit Transfer": curate_sample(
            pacs008,
            [
                "exchangeRate",
                "chargeBearer",
                "serviceLevel",
                "instructedAmount",
                "instructedCurrency",
                "purpose",
            ],
        ),
        "pacs.009 - Bank-to-Bank Transfer": curate_sample(
            pacs009,
            [
                "instructingAgent",
                "instructedAgent",
                "intermediaryAgent1",
                "chargeBearer",
                "serviceLevel",
            ],
        ),
        "pacs.004 - Payment Return": curate_sample(
            pacs004,
            [
                "originalUetr",
                "returnReason",
                "originalPaymentRef",
            ],
        ),
        "pain.001 - Payment Initiation": curate_sample(
            pain001,
            [
                "initiatingParty",
                "numberOfTransactions",
                "controlSum",
                "requestedExecutionDate",
                "paymentMethod",
            ],
        ),
        "pain.008 - Direct Debit": curate_sample(
            pain008,
            [
                "mandateId",
                "creditorSchemeId",
                "sequenceType",
                "requestedCollectionDate",
                "directDebitInfo",
            ],
        ),
    }

    # Count by type
    pipeline = [
        {"$group": {"_id": "$messageType", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    cursor = db.payments.aggregate(pipeline)
    type_distribution = {}
    async for doc in cursor:
        type_distribution[doc["_id"]] = doc["count"]

    return {
        "title": "Flexible Schema - Polymorphic Messages",
        "description": "ISO 20022 has 775+ message types with different structures. "
        "MongoDB stores them all in a single collection without ALTER TABLE. "
        "Each document carries exactly the fields it needs - no NULLs, no sparse columns.",
        "benefit": "No schema migrations, no ALTER TABLE downtime, no NULL columns. "
        "Adding a new message type tomorrow requires zero database changes.",
        "samples": samples,
        "typeDistribution": type_distribution,
        "commonFields": [
            "messageType",
            "uetr",
            "settlementAmount",
            "settlementCurrency",
            "status",
            "statusHistory",
            "debtor",
            "creditor",
            "debtorAgent",
            "creditorAgent",
            "createdAt",
        ],
        "typeSpecificFields": {
            "pacs.008": [
                "exchangeRate",
                "chargeBearer",
                "serviceLevel",
                "instructedAmount",
                "purpose",
            ],
            "pacs.009": ["instructingAgent", "instructedAgent", "intermediaryAgent1"],
            "pacs.004": ["originalUetr", "returnReason", "originalPaymentRef"],
            "pain.001": [
                "initiatingParty",
                "numberOfTransactions",
                "controlSum",
                "requestedExecutionDate",
            ],
            "pain.008": [
                "mandateId",
                "creditorSchemeId",
                "sequenceType",
                "requestedCollectionDate",
            ],
        },
        "relationalAlternative": {
            "approach": "Table-per-type or sparse single table",
            "tables": [
                "payments (shared columns)",
                "credit_transfer_details (pacs.008 specific)",
                "bank_transfer_details (pacs.009 specific)",
                "payment_return_details (pacs.004 specific)",
                "payment_initiation_details (pain.001 specific)",
                "direct_debit_details (pain.008 specific)",
            ],
            "problem": "Every query needs JOINs. Every new type needs ALTER TABLE + migration + ORM update.",
        },
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
                "byMessageType": [
                    {
                        "$group": {
                            "_id": "$messageType",
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
        "in a single pass over the data - across ALL payment types simultaneously.",
        "benefit": "No data movement to app layer. Real-time analytics on live data. "
        "Single pipeline replaces multiple SQL queries with GROUP BY. "
        "Works across all polymorphic document types in one pass.",
        "pipelineSummary": "$facet with 5 parallel aggregations (byStatus, byCurrency, byMessageType, byCountryCorridor, totalStats)",
        "pipelineJson": pipeline,
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
        "status must be a valid ISO 20022 code, amounts must be Decimal128. "
        "Type-specific fields are validated when present, but not required for all types.",
        "benefit": "Data quality enforced regardless of which application writes data. "
        "validationLevel: 'moderate' allows gradual migration. "
        "validationAction: 'warn' logs violations without rejecting writes. "
        "Shared + type-specific fields validated in one schema.",
        "validator": validator,
        "validatedFields": {
            "messageType": "enum: pacs.008, pacs.009, pacs.004, pain.001, pain.008",
            "uetr": "UUID v4 pattern regex (^[0-9a-f]{8}-...)",
            "settlementCurrency": "^[A-Z]{3}$ (ISO 4217)",
            "status": "enum: ACTC, ACCP, ACSP, ACSC, RJCT, PDNG, CANC",
            "settlementAmount": "bsonType: decimal (Decimal128)",
            "statusHistory": "maxItems: 50",
            "charges": "maxItems: 20",
            "returnReason": "object with code + description (pacs.004 only)",
            "numberOfTransactions": "bsonType: int (pain.001 only)",
            "sequenceType": "enum: FRST, RCUR, FNAL, OOFF (pain.008 only)",
        },
    }


@router.get("/atomic-operations")
async def demo_atomic_operations():
    """
    Demonstrates MongoDB's atomic operations on rich documents.
    """
    db = get_database()

    # Fetch a real payment to show realistic UETR in the example
    sample = await db.payments.find_one({"status": {"$in": ["ACSP", "ACSC"]}})
    sample_uetr = sample.get("uetr", "eb6305c9-...") if sample else "eb6305c9-..."
    sample_history = serialize_doc(sample).get("statusHistory", []) if sample else []

    return {
        "title": "Atomic Operations - No Distributed Transactions Needed",
        "description": "MongoDB updates the payment status AND appends to status history "
        "in a single atomic operation. No BEGIN/COMMIT/ROLLBACK needed. "
        "Works identically across all polymorphic payment types.",
        "benefit": "Eliminates race conditions. No partial updates. "
        "Single document updates are always atomic in MongoDB.",
        "exampleOperation": {
            "operation": "Update payment status",
            "mongoCommand": f"""db.payments.updateOne(
  {{ uetr: "{sample_uetr[:18]}..." }},
  {{
    $set: {{ status: "ACSC", statusReason: null }},
    $push: {{
      statusHistory: {{
        status: "ACSC",
        timestamp: ISODate(),
        reason: null
      }}
    }}
  }}
)""",
            "equivalentSQL": """BEGIN TRANSACTION;

UPDATE payments
SET status = 'ACSC'
WHERE uetr = '...';

INSERT INTO payment_status_log
  (payment_id, status, timestamp)
VALUES (..., 'ACSC', NOW());

-- If either fails, need ROLLBACK
COMMIT;""",
        },
        "liveExample": {
            "uetr": sample_uetr,
            "statusHistory": sample_history[-3:]
            if len(sample_history) > 3
            else sample_history,
        },
    }


@router.get("/decimal128-precision")
async def demo_decimal_precision():
    """
    Demonstrates Decimal128 for financial precision.
    """
    db = get_database()

    # Show real payments with Decimal128 amounts
    pipeline = [
        {"$limit": 5},
        {
            "$project": {
                "_id": 0,
                "messageType": 1,
                "settlementAmount": 1,
                "settlementCurrency": 1,
                "uetr": {"$substr": ["$uetr", 0, 8]},
            }
        },
    ]
    samples = await db.payments.aggregate(pipeline).to_list(5)
    serialized_samples = [serialize_doc(s) for s in samples]

    return {
        "title": "Decimal128 - Financial-Grade Precision",
        "description": "MongoDB natively supports Decimal128 (IEEE 754-2008) for exact "
        "monetary arithmetic. No floating-point rounding errors. "
        "Every payment amount in this demo uses Decimal128.",
        "benefit": "0.1 + 0.2 = 0.3 (not 0.30000000000000004). "
        "34 significant digits. Range: +/-9.999...x10^6144. "
        "Critical for cross-currency settlement calculations.",
        "example": {
            "floatingPoint": "0.1 + 0.2 = 0.30000000000000004 (WRONG)",
            "decimal128": "Decimal128('0.1') + Decimal128('0.2') = Decimal128('0.3') (CORRECT)",
        },
        "liveAmounts": serialized_samples,
    }


@router.get("/ttl-indexes")
async def demo_ttl_indexes():
    """
    Demonstrates TTL indexes for automatic data lifecycle management.
    """
    db = get_database()

    # Count documents in TTL-managed collections
    notif_count = await db.notifications.count_documents({})
    status_report_count = await db.status_reports.count_documents({})

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
                "currentCount": status_report_count,
            },
            "notifications": {
                "ttl": "90 days (7,776,000 seconds)",
                "reason": "Real-time alerts, consumed quickly",
                "currentCount": notif_count,
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


@router.get("/vector-search")
async def demo_vector_search():
    """
    Demonstrates MongoDB Atlas Vector Search on polymorphic payment data.
    Shows how semantic search works across all payment types in one collection.
    """
    db = get_database()

    # Count embedded documents
    total = await db.payments.count_documents({})
    embedded = await db.payments.count_documents({"embedding": {"$exists": True}})

    # Get embedding dimension from a sample
    sample = await db.payments.find_one({"embedding": {"$exists": True}})
    dimensions = len(sample["embedding"]) if sample and sample.get("embedding") else 0

    # Get a sample of the text that was embedded
    sample_texts = []
    cursor = db.payments.find(
        {"embeddingText": {"$exists": True}},
        {"messageType": 1, "embeddingText": 1, "uetr": 1, "_id": 0},
    ).limit(5)
    async for doc in cursor:
        sample_texts.append(
            {
                "messageType": doc.get("messageType"),
                "uetr": doc.get("uetr", "")[:12] + "...",
                "embeddingText": doc.get("embeddingText", "")[:200],
            }
        )

    # Show the vector search index definitions
    indexes = {
        "payment_vector_index": {
            "purpose": "Natural language search + similar transaction detection",
            "path": "embedding",
            "dimensions": dimensions,
            "similarity": "cosine",
            "filters": ["messageType", "status", "settlementCurrency"],
        },
        "remittance_vector_index": {
            "purpose": "Smart remittance / invoice matching",
            "path": "remittanceEmbedding",
            "dimensions": dimensions,
            "similarity": "cosine",
            "filters": [],
        },
    }

    return {
        "title": "Vector Search - AI-Powered Payments Intelligence",
        "description": "MongoDB Atlas Vector Search enables semantic search across all polymorphic "
        "payment types in a single collection. Payment documents are embedded using Voyage Finance "
        "(a model purpose-built for financial data) and indexed for sub-second similarity queries. "
        "Natural language queries like 'large rejected transfers to Germany' find relevant payments "
        "without needing exact field names or ISO codes.",
        "benefit": "Semantic search across 5 payment types in one index. No separate search engine. "
        "Pre-filter by messageType, status, or currency BEFORE computing vector similarity. "
        "Same collection, same database, same query language -- just add $vectorSearch to the aggregation pipeline.",
        "coverage": {
            "totalPayments": total,
            "embeddedPayments": embedded,
            "coveragePercent": f"{embedded / total * 100:.0f}%" if total > 0 else "0%",
            "model": "voyage-finance-2",
            "dimensions": dimensions,
            "endpoint": "https://ai.mongodb.com/v1/embeddings",
        },
        "indexes": indexes,
        "useCases": [
            {
                "name": "Natural Language Payment Search",
                "description": "Search payments by describing what you need in plain English",
                "example": 'db.payments.aggregate([{ $vectorSearch: { index: "payment_vector_index", '
                'path: "embedding", queryVector: embed("large rejected transfers to Germany"), '
                "numCandidates: 300, limit: 15 } }])",
            },
            {
                "name": "Similar Transaction Detection",
                "description": "Given a suspicious payment, find structurally similar transactions for fraud analysis",
                "example": 'db.payments.aggregate([{ $vectorSearch: { index: "payment_vector_index", '
                'path: "embedding", queryVector: flaggedPayment.embedding, '
                "numCandidates: 200, limit: 10 } }])",
            },
            {
                "name": "Smart Remittance Matching",
                "description": "Match incoming invoice text to payments semantically -- handles typos and abbreviations",
                "example": 'db.payments.aggregate([{ $vectorSearch: { index: "remittance_vector_index", '
                'path: "remittanceEmbedding", queryVector: embed("Invoice 3974 from ACME"), '
                "numCandidates: 200, limit: 10 } }])",
            },
        ],
        "sampleTexts": sample_texts,
        "relationalAlternative": {
            "approach": "Separate Elasticsearch/OpenSearch cluster + ETL pipeline + sync logic",
            "problems": [
                "Data duplication across systems",
                "ETL lag means stale search results",
                "Separate infrastructure to manage and scale",
                "No pre-filtering on document fields without denormalization",
                "Cannot use $vectorSearch in the same aggregation pipeline as $match, $group, etc.",
            ],
        },
    }


@router.get("/indexing-strategies")
async def demo_indexing_strategies():
    """
    Demonstrates MongoDB's rich indexing capabilities for payment workloads:
    compound indexes, partial indexes, TTL indexes, unique constraints,
    nested field indexes, and vector search indexes.
    """
    db = get_database()

    # Gather live index info from the payments collection
    regular_indexes = []
    async for idx in db.payments.list_indexes():
        info = {
            "name": idx.get("name", ""),
            "key": {
                k: ("ASC" if v == 1 else "DESC" if v == -1 else str(v))
                for k, v in idx.get("key", {}).items()
            },
            "unique": idx.get("unique", False),
            "sparse": idx.get("sparse", False),
            "expireAfterSeconds": idx.get("expireAfterSeconds"),
            "partialFilterExpression": idx.get("partialFilterExpression"),
        }
        regular_indexes.append(info)

    search_indexes = []
    try:
        async for idx in db.payments.list_search_indexes():
            search_indexes.append(
                {
                    "name": idx.get("name", ""),
                    "type": idx.get("type", "search"),
                    "status": idx.get("status", ""),
                    "queryable": idx.get("queryable", False),
                }
            )
    except Exception:
        pass

    # Categorize indexes for display
    unique_indexes = [i for i in regular_indexes if i["unique"]]
    compound_indexes = [
        i
        for i in regular_indexes
        if len(i["key"]) > 1 and not i.get("partialFilterExpression")
    ]
    partial_indexes = [i for i in regular_indexes if i.get("partialFilterExpression")]
    ttl_indexes = [
        i for i in regular_indexes if i.get("expireAfterSeconds") is not None
    ]
    nested_indexes = [i for i in regular_indexes if any("." in k for k in i["key"])]

    # Count total indexes across key collections
    collections_to_check = [
        "payments",
        "agent_memory",
        "agent_messages",
        "investigations",
        "statements",
    ]
    total_indexes = 0
    for coll_name in collections_to_check:
        try:
            count = 0
            async for _ in db[coll_name].list_indexes():
                count += 1
            total_indexes += count
        except Exception:
            pass

    return {
        "title": "Indexing Strategies - Query Performance at Scale",
        "description": "MongoDB supports a rich set of index types to optimize every query pattern "
        "in a payment system. This demo uses compound indexes for multi-field queries, partial indexes "
        "to index only a subset of documents (e.g., only rejected payments or only pacs.004 returns), "
        "TTL indexes for automatic data expiry, unique constraints for business keys, nested field "
        "indexes for querying embedded documents, and vector search indexes for AI-powered search.",
        "benefit": "Partial indexes are a unique MongoDB advantage -- they index only documents matching "
        "a filter, saving storage and improving write performance. For a polymorphic collection, this "
        "means you can create type-specific indexes that only cover relevant documents. A partial index "
        "on returnReason.code WHERE messageType='pacs.004' is tiny compared to indexing every payment.",
        "stats": {
            "totalIndexesAcrossCollections": total_indexes,
            "paymentCollectionIndexes": len(regular_indexes),
            "vectorSearchIndexes": len(search_indexes),
        },
        "categories": {
            "compound": {
                "label": "Compound Indexes",
                "description": "Multi-field indexes that support queries filtering or sorting on multiple fields. "
                "MongoDB uses index prefix compression -- a compound index on {messageType, status, settlementDate} "
                "also satisfies queries on just {messageType} or {messageType, status}.",
                "count": len(compound_indexes),
                "examples": compound_indexes[:5],
            },
            "partial": {
                "label": "Partial Indexes",
                "description": "Index only the documents that match a filter expression. Perfect for polymorphic "
                "collections where type-specific fields only exist on a subset of documents. Dramatically reduces "
                "index size and write overhead compared to indexing every document.",
                "count": len(partial_indexes),
                "examples": partial_indexes,
            },
            "unique": {
                "label": "Unique Indexes",
                "description": "Enforce uniqueness on business keys like UETR, messageId, and statementId. "
                "Prevents duplicate payments at the database level -- no application logic needed.",
                "count": len(unique_indexes),
                "examples": unique_indexes[:4],
            },
            "ttl": {
                "label": "TTL Indexes",
                "description": "Automatically expire documents after a specified duration. "
                "Used for notifications (90 days), status reports (1 year), agent messages (24 hours), "
                "and episodic agent memory (variable TTL per document).",
                "count": len(ttl_indexes),
                "examples": ttl_indexes[:4],
            },
            "nested": {
                "label": "Nested Field Indexes",
                "description": "Index fields inside embedded documents and arrays. "
                "Query debtor.account.iban or creditor.address.country with full index support -- "
                "no separate table, no JOIN, just dot notation.",
                "count": len(nested_indexes),
                "examples": nested_indexes[:4],
            },
            "vectorSearch": {
                "label": "Atlas Vector Search Indexes",
                "description": "Dedicated indexes for vector similarity search with pre-filtering. "
                "Used for AI-powered payment search, remittance matching, and agent memory recall.",
                "count": len(search_indexes),
                "examples": search_indexes,
            },
        },
        "partialVsFullComparison": {
            "title": "Partial Index Advantage",
            "description": "Compare a partial index (only pacs.004 returns) vs a full index (all payments). "
            "In a collection with 200+ payments but only ~30 returns, the partial index is 85% smaller.",
            "examples": [
                {
                    "name": "Full index on originalUetr",
                    "definition": {"key": {"originalUetr": "ASC"}},
                    "scope": "All 230+ documents",
                    "problem": "originalUetr only exists on pacs.004 documents -- wastes space indexing NULLs",
                },
                {
                    "name": "Partial index on originalUetr WHERE pacs.004",
                    "definition": {
                        "key": {"originalUetr": "ASC"},
                        "partialFilterExpression": {"messageType": "pacs.004"},
                    },
                    "scope": "Only ~30 pacs.004 documents",
                    "benefit": "85% smaller index, faster writes, same query performance for return lookups",
                },
            ],
        },
        "relationalAlternative": {
            "approach": "Postgres: B-tree indexes only, no partial index on polymorphic data without views",
            "problems": [
                "No partial indexes on column values (Postgres partial indexes exist but can't filter on type-discriminator columns in a polymorphic table elegantly)",
                "Table-per-type means separate indexes per table -- no single polymorphic index",
                "No built-in TTL indexes -- requires pg_cron or triggers",
                "No vector search indexes -- requires pgvector extension",
                "Cannot index nested JSON fields efficiently without generated columns",
            ],
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
                "summary": "5 payment types in one collection, each with different fields. "
                "No ALTER TABLE. No migrations. No NULLs.",
                "endpoint": "/api/value-props/flexible-schema",
            },
            {
                "name": "Aggregation Framework",
                "icon": "BarChart3",
                "summary": "Real-time payment analytics computed server-side. "
                "$facet for parallel aggregations across all payment types.",
                "endpoint": "/api/value-props/aggregation-power",
            },
            {
                "name": "Schema Validation",
                "icon": "ShieldCheck",
                "summary": "Enforce ISO 20022 data quality (UETR format, currency codes, "
                "status enums) at the database level - shared + type-specific.",
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
            {
                "name": "Vector Search",
                "icon": "Brain",
                "summary": "AI-powered semantic search across all payment types. "
                "Natural language queries, fraud detection, and smart remittance matching -- "
                "all in the same database, no separate search engine.",
                "endpoint": "/api/value-props/vector-search",
            },
            {
                "name": "Indexing Strategies",
                "icon": "Search",
                "summary": "Compound, partial, TTL, unique, nested field, and vector indexes. "
                "Partial indexes index only matching documents -- 85% smaller for type-specific queries.",
                "endpoint": "/api/value-props/indexing-strategies",
            },
        ],
    }
