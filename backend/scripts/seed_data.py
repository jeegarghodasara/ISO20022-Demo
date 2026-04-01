"""
Seed script for ISO 20022 Payment System Demo.
Populates MongoDB with realistic demo data across all collections.

Usage: python scripts/seed_data.py
"""

import sys
import os
import uuid
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from pymongo import MongoClient
from bson import Decimal128
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "iso20022_payments")


def generate_uetr():
    return str(uuid.uuid4())


def generate_msg_id(prefix="MSG"):
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    short = uuid.uuid4().hex[:8]
    return f"{prefix}-{ts}-{short}"


def d128(val):
    return Decimal128(str(round(float(val), 2)))


def random_date(start_days_ago=60, end_days_ago=0):
    days = random.randint(end_days_ago, start_days_ago)
    dt = datetime.now(timezone.utc) - timedelta(
        days=days, hours=random.randint(0, 23), minutes=random.randint(0, 59)
    )
    return dt


# Reference data
BANKS = [
    {"bic": "DEUTDEFF", "name": "Deutsche Bank AG", "country": "DE"},
    {"bic": "BNPAFRPP", "name": "BNP Paribas", "country": "FR"},
    {"bic": "NWBKGB2L", "name": "NatWest Group", "country": "GB"},
    {"bic": "CHASUS33", "name": "JPMorgan Chase", "country": "US"},
    {"bic": "CITIUS33", "name": "Citibank", "country": "US"},
    {"bic": "HSBCHKHH", "name": "HSBC Hong Kong", "country": "HK"},
    {"bic": "ANZBAU3M", "name": "ANZ Banking Group", "country": "AU"},
    {"bic": "MABORBJP", "name": "Mizuho Bank", "country": "JP"},
    {"bic": "SBININBB", "name": "State Bank of India", "country": "IN"},
    {"bic": "BOFAUS3N", "name": "Bank of America", "country": "US"},
    {"bic": "UBSWCHZH", "name": "UBS Group AG", "country": "CH"},
    {"bic": "SCBLSGSG", "name": "Standard Chartered Singapore", "country": "SG"},
]

CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AUD", "CHF", "CAD", "SGD", "HKD", "INR"]

PEOPLE = [
    {
        "name": "John Schmidt",
        "country": "DE",
        "town": "Frankfurt",
        "iban": "DE89370400440532013000",
    },
    {
        "name": "Marie Dupont",
        "country": "FR",
        "town": "Paris",
        "iban": "FR7630006000011234567890189",
    },
    {
        "name": "James Wilson",
        "country": "GB",
        "town": "London",
        "iban": "GB29NWBK60161331926819",
    },
    {
        "name": "Sarah Johnson",
        "country": "US",
        "town": "New York",
        "iban": "US12345678901234567890",
    },
    {
        "name": "Kenji Tanaka",
        "country": "JP",
        "town": "Tokyo",
        "iban": "JP12345678901234567",
    },
    {
        "name": "Li Wei Chen",
        "country": "HK",
        "town": "Hong Kong",
        "iban": "HK12345678901234567890",
    },
    {
        "name": "Priya Sharma",
        "country": "IN",
        "town": "Mumbai",
        "iban": "IN12345678901234567890",
    },
    {
        "name": "Emma Thompson",
        "country": "AU",
        "town": "Sydney",
        "iban": "AU12345678901234567890",
    },
    {
        "name": "Hans Mueller",
        "country": "CH",
        "town": "Zurich",
        "iban": "CH9300762011623852957",
    },
    {
        "name": "Olivia Brown",
        "country": "SG",
        "town": "Singapore",
        "iban": "SG12345678901234567890",
    },
    {
        "name": "ACME Global Corp",
        "country": "US",
        "town": "Chicago",
        "iban": "US98765432109876543210",
    },
    {
        "name": "EuroTech GmbH",
        "country": "DE",
        "town": "Munich",
        "iban": "DE27100777770209299700",
    },
    {
        "name": "Sakura Trading Ltd",
        "country": "JP",
        "town": "Osaka",
        "iban": "JP98765432109876543",
    },
    {
        "name": "Thames Consulting",
        "country": "GB",
        "town": "Manchester",
        "iban": "GB82WEST12345698765432",
    },
    {
        "name": "Alpine Industries AG",
        "country": "CH",
        "town": "Geneva",
        "iban": "CH5604835012345678009",
    },
]

STATUSES = ["ACTC", "ACCP", "ACSP", "ACSC", "RJCT"]
STATUS_WEIGHTS = [5, 10, 15, 60, 10]

PURPOSES = [
    "SALA",
    "SUPP",
    "TRAD",
    "INTC",
    "CASH",
    "TAXS",
    "GOVT",
    "PENS",
    "SSBE",
    "LOAN",
]

REJECTION_REASONS = ["AC01", "AC04", "AC06", "AM04", "BE01", "RC01", "TM01"]


def build_status_history(final_status, created_at):
    history = [{"status": "ACTC", "timestamp": created_at, "reason": None}]
    status_chain = {
        "ACTC": [],
        "ACCP": ["ACTC"],
        "ACSP": ["ACTC", "ACCP"],
        "ACSC": ["ACTC", "ACCP", "ACSP"],
        "RJCT": ["ACTC"],
    }
    chain = status_chain.get(final_status, [])
    t = created_at
    for s in chain:
        if s == "ACTC":
            continue
        t = t + timedelta(seconds=random.randint(1, 30))
        history.append({"status": s, "timestamp": t, "reason": None})

    if final_status != "ACTC":
        t = t + timedelta(seconds=random.randint(1, 60))
        reason = random.choice(REJECTION_REASONS) if final_status == "RJCT" else None
        history.append({"status": final_status, "timestamp": t, "reason": reason})

    return history


def seed_participants(db):
    print("Seeding participants...")
    db.participants.delete_many({})
    participants = []
    for bank in BANKS:
        participants.append(
            {
                "bic": bank["bic"],
                "name": bank["name"],
                "country": bank["country"],
                "participantType": "FI",
                "networks": random.sample(
                    ["SWIFT", "SEPA", "TARGET2", "CHIPS", "Fedwire", "FedNow"],
                    k=random.randint(1, 3),
                ),
                "correspondents": [
                    {
                        "currency": random.choice(CURRENCIES),
                        "bic": random.choice(BANKS)["bic"],
                        "relationship": "nostro",
                    }
                    for _ in range(random.randint(1, 3))
                ],
                "status": "ACTIVE",
                "updatedAt": datetime.now(timezone.utc),
            }
        )
    db.participants.insert_many(participants)
    print(f"  Inserted {len(participants)} participants")


def seed_accounts(db):
    print("Seeding accounts...")
    db.accounts.delete_many({})
    accounts = []
    for person in PEOPLE:
        bank = random.choice(BANKS)
        accounts.append(
            {
                "iban": person["iban"],
                "currency": random.choice(CURRENCIES[:5]),
                "accountType": "CACC",
                "status": "ACTIVE",
                "owner": {
                    "name": person["name"],
                    "type": "ORG"
                    if any(
                        x in person["name"]
                        for x in ["Corp", "GmbH", "Ltd", "AG", "Trading"]
                    )
                    else "PRVT",
                    "address": {
                        "townName": person["town"],
                        "country": person["country"],
                    },
                },
                "servicer": {"bic": bank["bic"], "name": bank["name"]},
                "openedAt": datetime.now(timezone.utc)
                - timedelta(days=random.randint(365, 2000)),
                "closedAt": None,
            }
        )
    db.accounts.insert_many(accounts)
    print(f"  Inserted {len(accounts)} accounts")


def seed_payments(db, count=200):
    print(f"Seeding {count} payments...")
    db.payments.delete_many({})
    db.remittance_details.delete_many({})

    payments = []
    remittance_records = []

    for i in range(count):
        debtor = random.choice(PEOPLE)
        creditor = random.choice([p for p in PEOPLE if p["iban"] != debtor["iban"]])
        debtor_bank = random.choice(BANKS)
        creditor_bank = random.choice(
            [b for b in BANKS if b["bic"] != debtor_bank["bic"]]
        )

        status = random.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]
        created_at = random_date(60, 0)
        settlement_date = created_at + timedelta(days=random.choice([0, 1, 2]))
        currency = random.choice(CURRENCIES[:5])
        amount = round(random.uniform(100, 500000), 2)

        uetr = generate_uetr()
        msg_type = random.choices(
            ["pacs.008", "pacs.009", "pacs.004"], weights=[80, 15, 5], k=1
        )[0]

        payment = {
            "messageId": generate_msg_id(
                "PACS008" if msg_type == "pacs.008" else "PACS"
            ),
            "messageType": msg_type,
            "messageVersion": "001.014",
            "direction": random.choice(["inbound", "outbound"]),
            "createdAt": created_at,
            "receivedAt": created_at + timedelta(seconds=random.randint(0, 5)),
            "uetr": uetr,
            "endToEndId": generate_msg_id("E2E"),
            "txId": generate_msg_id("TX"),
            "instrId": generate_msg_id("INSTR"),
            "batchId": None,
            "batchMessageId": None,
            "sequenceInBatch": None,
            "settlementAmount": d128(amount),
            "settlementCurrency": currency,
            "settlementDate": settlement_date,
            "settlementMethod": random.choice(["CLRG", "INDA", "INGA", "COVE"]),
            "instructedAmount": d128(amount * random.uniform(0.95, 1.05)),
            "instructedCurrency": currency
            if random.random() > 0.3
            else random.choice(CURRENCIES),
            "exchangeRate": d128(random.uniform(0.8, 1.2))
            if random.random() > 0.7
            else d128(1.0),
            "debtor": {
                "name": debtor["name"],
                "address": {"townName": debtor["town"], "country": debtor["country"]},
                "account": {"iban": debtor["iban"]},
            },
            "creditor": {
                "name": creditor["name"],
                "address": {
                    "townName": creditor["town"],
                    "country": creditor["country"],
                },
                "account": {"iban": creditor["iban"]},
            },
            "debtorAgent": {"bic": debtor_bank["bic"], "name": debtor_bank["name"]},
            "creditorAgent": {
                "bic": creditor_bank["bic"],
                "name": creditor_bank["name"],
            },
            "instructingAgent": {"bic": debtor_bank["bic"]},
            "instructedAgent": {"bic": creditor_bank["bic"]},
            "intermediaryAgent1": None,
            "chargeBearer": random.choice(["SHAR", "DEBT", "CRED"]),
            "charges": [
                {
                    "amount": d128(random.uniform(1, 50)),
                    "currency": currency,
                    "agentBic": debtor_bank["bic"],
                }
            ]
            if random.random() > 0.5
            else [],
            "priority": random.choice(["NORM", "HIGH"]),
            "serviceLevel": random.choice(["SEPA", "URGP", "NURG"]),
            "purpose": random.choice(PURPOSES),
            "status": status,
            "statusReason": random.choice(REJECTION_REASONS)
            if status == "RJCT"
            else None,
            "statusHistory": build_status_history(status, created_at),
            "remittanceSummary": {
                "type": random.choice(["structured", "unstructured"]),
                "unstructuredText": f"Payment for invoice INV-{random.randint(1000, 9999)}"
                if random.random() > 0.5
                else None,
                "documentCount": random.randint(1, 5),
                "totalRemittedAmount": d128(amount),
            },
            "originalMessageRef": None,
            "archivedAt": None,
        }

        # If pacs.004 (return), reference an original payment
        if msg_type == "pacs.004" and payments:
            orig = random.choice(payments)
            payment["originalPaymentRef"] = orig["uetr"]

        payments.append(payment)

        # Create remittance details for some payments
        if random.random() > 0.5:
            num_docs = random.randint(1, 5)
            for j in range(num_docs):
                doc_types = ["CINV", "CREN", "DEBN", "PUOR"]
                rem_amt = round(amount / num_docs, 2)
                remittance_records.append(
                    {
                        "paymentUetr": uetr,
                        "paymentEndToEndId": payment["endToEndId"],
                        "documentType": random.choice(doc_types),
                        "documentNumber": f"INV-{random.randint(2024, 2026)}-{random.randint(1000, 9999)}",
                        "relatedDate": created_at
                        - timedelta(days=random.randint(1, 30)),
                        "duePyblAmt": d128(rem_amt * 1.1),
                        "discountAmt": d128(rem_amt * 0.02)
                        if random.random() > 0.5
                        else d128(0),
                        "taxAmt": d128(rem_amt * 0.1),
                        "remittedAmt": d128(rem_amt),
                        "currency": currency,
                        "creditorRef": f"RF{random.randint(10, 99)}{random.randint(100000000, 999999999)}",
                        "creditorRefType": "SCOR",
                        "additionalInfo": random.choice(
                            [
                                "Monthly consulting services",
                                "Q1 software license",
                                "Hardware procurement",
                                "Annual maintenance contract",
                                "Professional services - March",
                                None,
                            ]
                        ),
                    }
                )

    db.payments.insert_many(payments)
    print(f"  Inserted {len(payments)} payments")

    if remittance_records:
        db.remittance_details.insert_many(remittance_records)
        print(f"  Inserted {len(remittance_records)} remittance details")


def seed_statements(db):
    print("Seeding statements and entries...")
    db.statements.delete_many({})
    db.statement_entries.delete_many({})

    statements = []
    all_entries = []

    # Create statements for some accounts
    accounts_for_stmts = random.sample(PEOPLE, min(8, len(PEOPLE)))

    for person in accounts_for_stmts:
        for days_ago in [0, 1, 2, 3, 7, 14, 30]:
            stmt_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
            stmt_id = f"STMT-{stmt_date.strftime('%Y%m%d')}-{person['iban'][-4:]}-{uuid.uuid4().hex[:6]}"

            opening = round(random.uniform(10000, 200000), 2)
            num_entries = random.randint(3, 15)
            total_credits = round(random.uniform(5000, 50000), 2)
            total_debits = round(random.uniform(3000, 40000), 2)
            closing = round(opening + total_credits - total_debits, 2)

            stmt = {
                "statementId": stmt_id,
                "messageId": generate_msg_id("CAMT053"),
                "accountIban": person["iban"],
                "accountCurrency": random.choice(CURRENCIES[:3]),
                "accountOwner": person["name"],
                "statementDate": stmt_date,
                "fromDate": stmt_date.replace(hour=0, minute=0, second=0),
                "toDate": stmt_date.replace(hour=23, minute=59, second=59),
                "sequenceNumber": 365 - days_ago,
                "pageNumber": 1,
                "lastPage": True,
                "balances": {
                    "openingBooked": {
                        "amount": d128(opening),
                        "creditDebit": "CRDT",
                        "date": stmt_date,
                    },
                    "closingBooked": {
                        "amount": d128(closing),
                        "creditDebit": "CRDT" if closing > 0 else "DBIT",
                        "date": stmt_date,
                    },
                    "closingAvailable": {
                        "amount": d128(closing * 0.95),
                        "creditDebit": "CRDT",
                        "date": stmt_date,
                    },
                },
                "summary": {
                    "entryCount": num_entries,
                    "totalCredits": {
                        "count": num_entries // 2 + 1,
                        "amount": d128(total_credits),
                    },
                    "totalDebits": {
                        "count": num_entries // 2,
                        "amount": d128(total_debits),
                    },
                },
            }
            statements.append(stmt)

            # Create entries
            for e in range(num_entries):
                is_credit = e < (num_entries // 2 + 1)
                entry_amt = round(random.uniform(100, 10000), 2)
                counterparty = random.choice(
                    [p for p in PEOPLE if p["iban"] != person["iban"]]
                )

                entry = {
                    "statementId": stmt_id,
                    "accountIban": person["iban"],
                    "entryAmount": d128(entry_amt),
                    "creditDebit": "CRDT" if is_credit else "DBIT",
                    "status": "BOOK",
                    "bookingDate": stmt_date,
                    "valueDate": stmt_date,
                    "accountServicerRef": f"ASR-{random.randint(10000, 99999)}",
                    "bankTxCode": {
                        "domain": "PMNT",
                        "family": "RCDT" if is_credit else "ICDT",
                        "subFamily": "ESCT",
                    },
                    "endToEndId": generate_msg_id("E2E"),
                    "uetr": generate_uetr(),
                    "txId": generate_msg_id("TX"),
                    "counterpartyName": counterparty["name"],
                    "counterpartyIban": counterparty["iban"],
                    "counterpartyBic": random.choice(BANKS)["bic"],
                    "remittanceInfo": random.choice(
                        [
                            f"Invoice INV-{random.randint(1000, 9999)}",
                            "Monthly payment",
                            "Service fee",
                            f"PO-{random.randint(100, 999)}",
                            None,
                        ]
                    ),
                }
                all_entries.append(entry)

    if statements:
        db.statements.insert_many(statements)
        print(f"  Inserted {len(statements)} statements")
    if all_entries:
        db.statement_entries.insert_many(all_entries)
        print(f"  Inserted {len(all_entries)} statement entries")


def seed_notifications(db):
    print("Seeding notifications...")
    db.notifications.delete_many({})

    notifications = []
    for _ in range(50):
        person = random.choice(PEOPLE)
        counterparty = random.choice([p for p in PEOPLE if p != person])
        is_credit = random.random() > 0.4
        created = random_date(30, 0)

        notifications.append(
            {
                "messageId": generate_msg_id("NOTIF"),
                "accountIban": person["iban"],
                "createdAt": created,
                "entryAmount": d128(random.uniform(100, 50000)),
                "creditDebit": "CRDT" if is_credit else "DBIT",
                "status": "BOOK",
                "bookingDate": created,
                "valueDate": created,
                "bankTxCode": {
                    "domain": "PMNT",
                    "family": "RCDT" if is_credit else "ICDT",
                    "subFamily": "ESCT",
                },
                "endToEndId": generate_msg_id("E2E"),
                "uetr": generate_uetr(),
                "counterpartyName": counterparty["name"],
                "counterpartyIban": counterparty["iban"],
                "remittanceInfo": f"Invoice INV-{random.randint(1000, 9999)}",
            }
        )

    db.notifications.insert_many(notifications)
    print(f"  Inserted {len(notifications)} notifications")


def seed_investigations(db):
    print("Seeding investigations...")
    db.investigations.delete_many({})

    # Get some UETRs from payments
    payment_uetrs = [p["uetr"] for p in db.payments.find({}, {"uetr": 1}).limit(20)]

    investigations = []
    inv_types = ["camt.056", "camt.026", "camt.027", "camt.087"]
    inv_reasons = ["DUPL", "CUST", "AGNT", "TECH", "FRAD", "AM09"]
    inv_statuses = ["OPEN", "PENDING", "RESOLVED", "CLOSED"]

    for i in range(15):
        created = random_date(30, 0)
        status = random.choice(inv_statuses)
        case_id = generate_msg_id("INV")
        msg_type = random.choice(inv_types)

        messages = [
            {
                "messageId": generate_msg_id(msg_type.replace(".", "").upper()),
                "messageType": msg_type,
                "direction": "outbound",
                "timestamp": created,
                "summary": f"Investigation initiated - {random.choice(inv_reasons)}",
            }
        ]

        if status in ["RESOLVED", "CLOSED"]:
            messages.append(
                {
                    "messageId": generate_msg_id("CAMT029"),
                    "messageType": "camt.029",
                    "direction": "inbound",
                    "timestamp": created + timedelta(hours=random.randint(1, 72)),
                    "summary": "Resolution received",
                }
            )

        investigation = {
            "caseId": case_id,
            "messageId": messages[0]["messageId"],
            "messageType": msg_type,
            "createdAt": created,
            "originalUetr": random.choice(payment_uetrs)
            if payment_uetrs
            else generate_uetr(),
            "originalEndToEndId": generate_msg_id("E2E"),
            "originalMessageId": generate_msg_id("PACS008"),
            "originalMessageType": "pacs.008",
            "originalAmount": d128(random.uniform(1000, 100000)),
            "originalCurrency": random.choice(CURRENCIES[:5]),
            "reason": random.choice(inv_reasons),
            "reasonDescription": random.choice(
                [
                    "Duplicate payment detected",
                    "Customer requested cancellation",
                    "Incorrect beneficiary details",
                    "Suspected fraudulent transaction",
                    "Technical processing error",
                    "Amount discrepancy",
                ]
            ),
            "requestedAction": random.choice(
                ["cancellation", "modification", "investigation"]
            ),
            "initiator": {
                "bic": random.choice(BANKS)["bic"],
                "name": random.choice(BANKS)["name"],
            },
            "respondent": {
                "bic": random.choice(BANKS)["bic"],
                "name": random.choice(BANKS)["name"],
            },
            "status": status,
            "resolution": random.choice(["ACCP", "RJCT"])
            if status in ["RESOLVED", "CLOSED"]
            else None,
            "resolvedAt": created + timedelta(hours=random.randint(1, 72))
            if status in ["RESOLVED", "CLOSED"]
            else None,
            "resolutionDetails": "Investigation resolved per correspondent response"
            if status in ["RESOLVED", "CLOSED"]
            else None,
            "messages": messages,
        }
        investigations.append(investigation)

    db.investigations.insert_many(investigations)
    print(f"  Inserted {len(investigations)} investigations")


def seed_mandates(db):
    print("Seeding mandates...")
    db.mandates.delete_many({})

    mandates = []
    frequencies = ["MNTH", "QURT", "YEAR"]
    seq_types = ["FRST", "RCUR", "FNAL", "OOFF"]
    mandate_statuses = ["ACTV", "ACTV", "ACTV", "SUSP", "CANC"]

    for i in range(20):
        creditor = random.choice(
            [
                p
                for p in PEOPLE
                if any(
                    x in p["name"]
                    for x in [
                        "Corp",
                        "GmbH",
                        "Ltd",
                        "AG",
                        "Trading",
                        "Consulting",
                        "Industries",
                    ]
                )
            ]
        )
        debtor = random.choice([p for p in PEOPLE if p != creditor])
        created = random_date(365, 0)

        mandates.append(
            {
                "mandateId": generate_msg_id("MNDT"),
                "messageType": "pain.009",
                "creditor": {
                    "name": creditor["name"],
                    "id": {
                        "orgId": {
                            "lei": f"5299{random.randint(100000000000, 999999999999)}55"
                        }
                    },
                    "account": {"iban": creditor["iban"]},
                    "agent": {"bic": random.choice(BANKS)["bic"]},
                },
                "debtor": {
                    "name": debtor["name"],
                    "account": {"iban": debtor["iban"]},
                    "agent": {"bic": random.choice(BANKS)["bic"]},
                },
                "frequency": random.choice(frequencies),
                "firstCollectionDate": created + timedelta(days=30),
                "finalCollectionDate": None
                if random.random() > 0.3
                else created + timedelta(days=365),
                "maxAmount": d128(random.uniform(100, 5000)),
                "sequenceType": random.choice(seq_types),
                "status": random.choice(mandate_statuses),
                "createdAt": created,
                "lastCollectionDate": created + timedelta(days=random.randint(0, 60))
                if random.random() > 0.3
                else None,
                "amendmentHistory": [],
            }
        )

    db.mandates.insert_many(mandates)
    print(f"  Inserted {len(mandates)} mandates")


def seed_status_reports(db):
    print("Seeding status reports...")
    db.status_reports.delete_many({})

    # Get some payments for reference
    payments = list(
        db.payments.find(
            {}, {"uetr": 1, "endToEndId": 1, "txId": 1, "messageId": 1, "status": 1}
        ).limit(50)
    )

    reports = []
    for i in range(30):
        created = random_date(30, 0)
        batch = random.sample(payments, min(random.randint(1, 5), len(payments)))

        report = {
            "messageId": generate_msg_id("SR"),
            "createdAt": created,
            "originalMessageId": batch[0]["messageId"]
            if batch
            else generate_msg_id("PACS008"),
            "originalMessageType": "pacs.008",
            "groupStatus": None,
            "transactions": [
                {
                    "originalUetr": p["uetr"],
                    "originalEndToEndId": p.get("endToEndId", ""),
                    "originalTxId": p.get("txId", ""),
                    "status": p.get("status", "ACSP"),
                    "reasonCode": random.choice(REJECTION_REASONS)
                    if p.get("status") == "RJCT"
                    else None,
                    "reasonInfo": None,
                    "charges": [],
                }
                for p in batch
            ],
            "direction": "inbound",
            "processed": True,
            "processedAt": created + timedelta(seconds=random.randint(1, 10)),
        }
        reports.append(report)

    db.status_reports.insert_many(reports)
    print(f"  Inserted {len(reports)} status reports")


def seed_payment_initiations(db):
    print("Seeding payment initiations...")
    db.payment_initiations.delete_many({})

    initiations = []
    for i in range(10):
        initiator = random.choice(
            [
                p
                for p in PEOPLE
                if any(x in p["name"] for x in ["Corp", "GmbH", "Ltd", "AG"])
            ]
        )
        created = random_date(30, 0)
        num_txns = random.randint(3, 20)
        total = round(random.uniform(10000, 500000), 2)
        rejected = random.randint(0, min(2, num_txns))

        uetrs = [generate_uetr() for _ in range(num_txns)]

        initiations.append(
            {
                "messageId": generate_msg_id("PAIN001"),
                "messageType": "pain.001",
                "messageVersion": "001.013",
                "createdAt": created,
                "initiatingParty": {
                    "name": initiator["name"],
                    "id": {"orgId": {"bic": random.choice(BANKS)["bic"]}},
                },
                "totalTransactions": num_txns,
                "controlSum": d128(total),
                "paymentInfoId": generate_msg_id("PMTINF"),
                "paymentMethod": "TRF",
                "requestedExecutionDate": created
                + timedelta(days=random.choice([0, 1, 2])),
                "priority": random.choice(["NORM", "HIGH"]),
                "serviceLevel": random.choice(["SEPA", "URGP"]),
                "debtor": {
                    "name": initiator["name"],
                    "account": {"iban": initiator["iban"]},
                },
                "debtorAgent": {"bic": random.choice(BANKS)["bic"]},
                "status": random.choice(["ACCP", "ACSP", "PART"]),
                "processedCount": num_txns - rejected,
                "rejectedCount": rejected,
                "generatedPaymentUetrs": uetrs,
            }
        )

    db.payment_initiations.insert_many(initiations)
    print(f"  Inserted {len(initiations)} payment initiations")


def main():
    print(f"Connecting to MongoDB: {MONGODB_URI}")
    client = MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]

    print(f"Database: {DATABASE_NAME}")
    print("=" * 60)

    seed_participants(db)
    seed_accounts(db)
    seed_payments(db, count=200)
    seed_statements(db)
    seed_notifications(db)
    seed_investigations(db)
    seed_mandates(db)
    seed_status_reports(db)
    seed_payment_initiations(db)

    print("=" * 60)
    print("Seed data complete!")
    print()

    # Print collection stats
    for name in db.list_collection_names():
        count = db[name].count_documents({})
        print(f"  {name}: {count} documents")

    client.close()


if __name__ == "__main__":
    main()
