from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from app.config import settings

client: AsyncIOMotorClient = None
db = None


async def connect_to_mongo():
    global client, db
    client = AsyncIOMotorClient(
        settings.mongodb_uri,
        maxPoolSize=50,
        minPoolSize=10,
        maxIdleTimeMS=30000,
        connectTimeoutMS=5000,
        serverSelectionTimeoutMS=5000,
        retryWrites=True,
        retryReads=True,
        w="majority",
    )
    db = client[settings.database_name]
    await create_indexes()
    await setup_schema_validation()
    print(f"Connected to MongoDB: {settings.database_name}")


async def close_mongo_connection():
    global client
    if client:
        client.close()
        print("MongoDB connection closed")


def get_database():
    return db


async def create_indexes():
    """Create all indexes - demonstrates MongoDB's flexible indexing."""
    # payments collection
    await db.payments.create_index([("uetr", ASCENDING)], unique=True)
    await db.payments.create_index([("endToEndId", ASCENDING)])
    await db.payments.create_index([("messageId", ASCENDING)])
    await db.payments.create_index([("messageType", ASCENDING)])
    await db.payments.create_index([("settlementDate", ASCENDING)])
    await db.payments.create_index(
        [("status", ASCENDING), ("settlementDate", DESCENDING)]
    )
    await db.payments.create_index(
        [
            ("messageType", ASCENDING),
            ("status", ASCENDING),
            ("settlementDate", DESCENDING),
        ]
    )
    await db.payments.create_index(
        [("debtor.account.iban", ASCENDING), ("settlementDate", DESCENDING)]
    )
    await db.payments.create_index(
        [("creditor.account.iban", ASCENDING), ("settlementDate", DESCENDING)]
    )
    await db.payments.create_index(
        [("debtorAgent.bic", ASCENDING), ("settlementDate", DESCENDING)]
    )
    await db.payments.create_index(
        [("creditorAgent.bic", ASCENDING), ("settlementDate", DESCENDING)]
    )
    await db.payments.create_index(
        [("settlementCurrency", ASCENDING), ("settlementDate", ASCENDING)]
    )
    await db.payments.create_index(
        [("batchId", ASCENDING), ("sequenceInBatch", ASCENDING)]
    )
    # pacs.004 specific: look up returns by original payment
    await db.payments.create_index([("originalUetr", ASCENDING)])
    # pain.008 specific: look up direct debits by mandate
    await db.payments.create_index([("mandateId", ASCENDING)])

    # payment_initiations collection
    await db.payment_initiations.create_index([("messageId", ASCENDING)], unique=True)
    await db.payment_initiations.create_index([("status", ASCENDING)])
    await db.payment_initiations.create_index([("requestedExecutionDate", ASCENDING)])

    # status_reports collection
    await db.status_reports.create_index([("originalMessageId", ASCENDING)])
    await db.status_reports.create_index([("transactions.originalUetr", ASCENDING)])
    await db.status_reports.create_index(
        [("createdAt", ASCENDING)],
        expireAfterSeconds=31536000,  # TTL: 1 year
    )

    # statements collection
    await db.statements.create_index(
        [("accountIban", ASCENDING), ("statementDate", DESCENDING)]
    )
    await db.statements.create_index([("statementId", ASCENDING)], unique=True)

    # statement_entries collection
    await db.statement_entries.create_index(
        [("statementId", ASCENDING), ("bookingDate", DESCENDING)]
    )
    await db.statement_entries.create_index(
        [("accountIban", ASCENDING), ("bookingDate", DESCENDING)]
    )
    await db.statement_entries.create_index([("uetr", ASCENDING)])

    # notifications collection
    await db.notifications.create_index(
        [("accountIban", ASCENDING), ("createdAt", DESCENDING)]
    )
    await db.notifications.create_index([("uetr", ASCENDING)])
    await db.notifications.create_index(
        [("createdAt", ASCENDING)],
        expireAfterSeconds=7776000,  # TTL: 90 days
    )

    # remittance_details collection
    await db.remittance_details.create_index([("paymentUetr", ASCENDING)])
    await db.remittance_details.create_index([("documentNumber", ASCENDING)])
    await db.remittance_details.create_index([("creditorRef", ASCENDING)])

    # investigations collection
    await db.investigations.create_index([("caseId", ASCENDING)], unique=True)
    await db.investigations.create_index([("originalUetr", ASCENDING)])
    await db.investigations.create_index(
        [("status", ASCENDING), ("createdAt", DESCENDING)]
    )

    # mandates collection
    await db.mandates.create_index([("mandateId", ASCENDING)], unique=True)
    await db.mandates.create_index([("debtor.account.iban", ASCENDING)])
    await db.mandates.create_index([("status", ASCENDING)])

    # accounts collection
    await db.accounts.create_index([("iban", ASCENDING)], unique=True)

    # participants collection
    await db.participants.create_index([("bic", ASCENDING)], unique=True)
    await db.participants.create_index([("networks", ASCENDING)])

    # original_messages collection
    await db.original_messages.create_index([("messageId", ASCENDING)])

    print("All indexes created successfully")


async def setup_schema_validation():
    """
    MongoDB VALUE PROP: Schema Validation for Polymorphic Data
    Enforce data quality at the database level with flexible JSON Schema validation.

    This is a key MongoDB advantage for ISO 20022: different message types
    (pacs.008, pacs.009, pacs.004, pain.001, pain.008) share common required fields
    but each type has its own additional fields. MongoDB validates the common
    structure while allowing type-specific fields to vary - impossible with a
    single rigid relational table without sparse columns or table-per-type patterns.
    """
    payments_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "messageType",
                "uetr",
                "settlementAmount",
                "settlementCurrency",
                "status",
            ],
            "properties": {
                "messageType": {
                    "bsonType": "string",
                    "enum": [
                        "pacs.008",
                        "pacs.009",
                        "pacs.004",
                        "pain.001",
                        "pain.008",
                    ],
                    "description": "ISO 20022 message type - determines which type-specific fields are present",
                },
                "uetr": {
                    "bsonType": "string",
                    "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
                    "description": "UUID v4 format UETR",
                },
                "settlementAmount": {
                    "bsonType": "decimal",
                    "description": "Decimal128 for monetary precision",
                },
                "settlementCurrency": {
                    "bsonType": "string",
                    "pattern": "^[A-Z]{3}$",
                    "description": "ISO 4217 currency code",
                },
                "status": {
                    "bsonType": "string",
                    "enum": ["ACTC", "ACCP", "ACSP", "ACSC", "RJCT", "PDNG", "CANC"],
                    "description": "ISO 20022 payment status code",
                },
                "statusHistory": {"bsonType": "array", "maxItems": 50},
                "charges": {"bsonType": "array", "maxItems": 20},
                # -- Type-specific fields validated when present --
                # pacs.004 return fields
                "returnReason": {
                    "bsonType": "object",
                    "properties": {
                        "code": {"bsonType": "string"},
                        "description": {"bsonType": "string"},
                    },
                    "description": "Present only for pacs.004 Payment Return messages",
                },
                # pain.001 initiation fields
                "numberOfTransactions": {
                    "bsonType": "int",
                    "description": "Present only for pain.001 Payment Initiation messages",
                },
                # pain.008 direct debit fields
                "sequenceType": {
                    "bsonType": "string",
                    "enum": ["FRST", "RCUR", "FNAL", "OOFF"],
                    "description": "Present only for pain.008 Direct Debit messages",
                },
            },
        }
    }

    try:
        existing = await db.list_collection_names()
        if "payments" in existing:
            await db.command(
                "collMod",
                "payments",
                validator=payments_validator,
                validationLevel="moderate",
                validationAction="warn",
            )
        else:
            await db.create_collection(
                "payments",
                validator=payments_validator,
                validationLevel="moderate",
                validationAction="warn",
            )
        print("Schema validation configured for payments collection (polymorphic)")
    except Exception as e:
        print(f"Schema validation setup note: {e}")
