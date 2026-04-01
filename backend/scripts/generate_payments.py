#!/usr/bin/env python3
"""
Generate random ISO 20022 payments by calling the demo REST API.

This is a standalone script that creates realistic payment data across all 5
polymorphic message types (pacs.008, pacs.009, pacs.004, pain.001, pain.008)
by POSTing to the running FastAPI backend.

Usage:
    python scripts/generate_payments.py                 # Generate 20 payments
    python scripts/generate_payments.py --count 50      # Generate 50 payments
    python scripts/generate_payments.py --type pacs.004 # Only payment returns
    python scripts/generate_payments.py --api http://localhost:8000  # Custom API URL

Requires: The backend server must be running (uvicorn app.main:app --port 8000)
"""

import argparse
import random
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

# ---------------------------------------------------------------------------
# Reference data — realistic names, IBANs, BICs, etc.
# ---------------------------------------------------------------------------

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
    {
        "name": "Nordic Shipping AS",
        "country": "NO",
        "town": "Oslo",
        "iban": "NO9386011117947",
    },
    {
        "name": "Maple Leaf Corp",
        "country": "CA",
        "town": "Toronto",
        "iban": "CA12345678901234",
    },
    {
        "name": "Dragon Tech Ltd",
        "country": "HK",
        "town": "Kowloon",
        "iban": "HK98765432101234567890",
    },
    {
        "name": "Pacific Trading Co",
        "country": "AU",
        "town": "Melbourne",
        "iban": "AU98765432109876543210",
    },
    {
        "name": "Sahara Logistics",
        "country": "AE",
        "town": "Dubai",
        "iban": "AE070331234567890123456",
    },
]

CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AUD", "CHF", "CAD", "SGD"]

REMITTANCE_TEMPLATES = [
    "Payment for invoice INV-{num}",
    "Monthly subscription - Ref {num}",
    "Consulting fees Q{q} {year}",
    "Salary payment - Employee {num}",
    "Purchase order PO-{num}",
    "Lease payment - Contract {num}",
    "Software license renewal SL-{num}",
    "Supply chain payment SC-{num}",
    "Service agreement SA-{num}",
    "Commission payout - Agent {num}",
    "Insurance premium - Policy {num}",
    "Freight charges - BL {num}",
    "Equipment rental ER-{num}",
    "Advertising services - Campaign {num}",
    "Maintenance contract MC-{num}",
]

RETURN_REASONS = [
    {"code": "AC04", "description": "Beneficiary account has been closed"},
    {"code": "AC06", "description": "Account is blocked, no debits allowed"},
    {"code": "AG01", "description": "Transaction type not supported for this account"},
    {"code": "AM05", "description": "Duplicate payment detected"},
    {"code": "BE04", "description": "Missing or incorrect creditor address"},
    {"code": "MD01", "description": "No valid mandate found"},
    {"code": "MS02", "description": "Customer has refused the payment"},
    {"code": "RC01", "description": "Bank identifier code is invalid or missing"},
    {"code": "FOCR", "description": "Return following a cancellation request"},
    {"code": "DUPL", "description": "Duplicate sending detected by the system"},
]

SEQUENCE_TYPES = [
    "FRST",
    "RCUR",
    "RCUR",
    "RCUR",
    "FNAL",
    "OOFF",
]  # weighted toward recurring

SERVICE_LEVELS = ["SEPA", "SWIFT", "INST", "BOOK"]

PURPOSES = ["SUPP", "SALA", "TRAD", "CASH", "DIVI", "GOVT", "PENS", "RENT", "TAXS"]

INITIATING_PARTIES = [
    {"name": "ACME Corp Treasury", "bic": "DEUTDEFF"},
    {"name": "EuroTech Finance Dept", "bic": "BNPAFRPP"},
    {"name": "Global Payments Hub", "bic": "CHASUS33"},
    {"name": "Pacific Payroll Services", "bic": "ANZBAU3M"},
    {"name": "Nordic Cash Management", "bic": "NWBKGB2L"},
    {"name": "Sakura Payables Center", "bic": "MABORBJP"},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def random_date(days_ahead=30):
    delta = timedelta(days=random.randint(1, days_ahead))
    return (datetime.now(timezone.utc) + delta).strftime("%Y-%m-%d")


def random_amount():
    """Generate a realistic payment amount with different magnitude ranges."""
    r = random.random()
    if r < 0.3:
        return round(random.uniform(100, 5000), 2)  # small
    elif r < 0.7:
        return round(random.uniform(5000, 100000), 2)  # medium
    elif r < 0.9:
        return round(random.uniform(100000, 500000), 2)  # large
    else:
        return round(random.uniform(500000, 5000000), 2)  # very large


def random_remittance():
    tpl = random.choice(REMITTANCE_TEMPLATES)
    return tpl.format(
        num=random.randint(1000, 9999),
        q=random.randint(1, 4),
        year=random.choice([2025, 2026]),
    )


def pick_two_different(lst):
    """Pick two different items from a list."""
    a = random.choice(lst)
    b = random.choice([x for x in lst if x["iban"] != a["iban"]])
    return a, b


def pick_two_different_banks():
    a = random.choice(BANKS)
    b = random.choice([x for x in BANKS if x["bic"] != a["bic"]])
    return a, b


# ---------------------------------------------------------------------------
# Payment generators — one per message type
# ---------------------------------------------------------------------------


def generate_pacs008():
    """Customer Credit Transfer (FI-to-FI)"""
    debtor, creditor = pick_two_different(PEOPLE)
    debtor_bank, creditor_bank = pick_two_different_banks()
    return {
        "messageType": "pacs.008",
        "amount": random_amount(),
        "currency": random.choice(CURRENCIES),
        "settlementDate": random_date(),
        "settlementMethod": "CLRG",
        "chargeBearer": random.choice(["SHAR", "DEBT", "CRED"]),
        "serviceLevel": random.choice(SERVICE_LEVELS),
        "purpose": random.choice(PURPOSES),
        "priority": random.choices(["NORM", "HIGH"], weights=[80, 20])[0],
        "remittanceInfo": random_remittance(),
        "debtor": {
            "name": debtor["name"],
            "address": {"country": debtor["country"]},
            "account": {"iban": debtor["iban"]},
        },
        "creditor": {
            "name": creditor["name"],
            "address": {"country": creditor["country"]},
            "account": {"iban": creditor["iban"]},
        },
        "debtorAgent": {"bic": debtor_bank["bic"]},
        "creditorAgent": {"bic": creditor_bank["bic"]},
    }


def generate_pacs009():
    """Bank-to-Bank Transfer (Financial Institution Credit Transfer)"""
    debtor_bank, creditor_bank = pick_two_different_banks()
    return {
        "messageType": "pacs.009",
        "amount": random_amount() * 2,  # bank transfers tend to be larger
        "currency": random.choice(CURRENCIES),
        "settlementDate": random_date(),
        "settlementMethod": "CLRG",
        "chargeBearer": "SHAR",
        "serviceLevel": random.choice(["SWIFT", "SEPA"]),
        "priority": random.choices(["NORM", "HIGH"], weights=[60, 40])[0],
        "remittanceInfo": f"Interbank settlement - {random.choice(['Liquidity', 'Cover', 'Funding', 'FX Settlement'])}",
        "debtor": {
            "name": debtor_bank["name"],
            "account": {
                "iban": f"{debtor_bank['country']}00{debtor_bank['bic']}0000001"
            },
        },
        "creditor": {
            "name": creditor_bank["name"],
            "account": {
                "iban": f"{creditor_bank['country']}00{creditor_bank['bic']}0000001"
            },
        },
        "debtorAgent": {"bic": debtor_bank["bic"]},
        "creditorAgent": {"bic": creditor_bank["bic"]},
        "instructingAgent": {"bic": debtor_bank["bic"]},
        "instructedAgent": {"bic": creditor_bank["bic"]},
    }


def generate_pacs004(existing_uetrs):
    """Payment Return — references an existing payment"""
    debtor, creditor = pick_two_different(PEOPLE)
    debtor_bank, creditor_bank = pick_two_different_banks()
    reason = random.choice(RETURN_REASONS)

    payload = {
        "messageType": "pacs.004",
        "amount": random_amount(),
        "currency": random.choice(CURRENCIES),
        "settlementDate": random_date(),
        "priority": "NORM",
        "remittanceInfo": f"Return: {reason['description']}",
        "originalUetr": random.choice(existing_uetrs)
        if existing_uetrs
        else "00000000-0000-4000-8000-000000000000",
        "returnReason": {
            "code": reason["code"],
            "description": reason["description"],
        },
        "debtor": {
            "name": debtor["name"],
            "account": {"iban": debtor["iban"]},
        },
        "creditor": {
            "name": creditor["name"],
            "account": {"iban": creditor["iban"]},
        },
        "debtorAgent": {"bic": debtor_bank["bic"]},
        "creditorAgent": {"bic": creditor_bank["bic"]},
    }
    return payload


def generate_pain001():
    """Payment Initiation — customer instructs bank"""
    debtor, creditor = pick_two_different(PEOPLE)
    debtor_bank, creditor_bank = pick_two_different_banks()
    initiator = random.choice(INITIATING_PARTIES)
    num_txns = random.choice([1, 1, 1, 2, 3, 5, 10])

    return {
        "messageType": "pain.001",
        "amount": random_amount(),
        "currency": random.choice(CURRENCIES),
        "settlementDate": random_date(),
        "requestedExecutionDate": random_date(days_ahead=14),
        "priority": random.choices(["NORM", "HIGH"], weights=[85, 15])[0],
        "remittanceInfo": random_remittance(),
        "numberOfTransactions": num_txns,
        "initiatingParty": {
            "name": initiator["name"],
            "id": {"orgId": {"bic": initiator["bic"]}},
        },
        "debtor": {
            "name": debtor["name"],
            "address": {"country": debtor["country"]},
            "account": {"iban": debtor["iban"]},
        },
        "creditor": {
            "name": creditor["name"],
            "address": {"country": creditor["country"]},
            "account": {"iban": creditor["iban"]},
        },
        "debtorAgent": {"bic": debtor_bank["bic"]},
        "creditorAgent": {"bic": creditor_bank["bic"]},
    }


def generate_pain008():
    """Direct Debit Initiation — creditor collects from debtor"""
    debtor, creditor = pick_two_different(PEOPLE)
    debtor_bank, creditor_bank = pick_two_different_banks()

    return {
        "messageType": "pain.008",
        "amount": random_amount(),
        "currency": random.choice(["EUR", "GBP", "CHF"]),  # DD mostly in Europe
        "settlementDate": random_date(),
        "requestedCollectionDate": random_date(days_ahead=14),
        "priority": "NORM",
        "remittanceInfo": random.choice(
            [
                f"Direct debit - Subscription {random.randint(1000, 9999)}",
                f"Monthly insurance premium - Policy {random.randint(100000, 999999)}",
                f"Utility payment - Account {random.randint(10000, 99999)}",
                f"Loan repayment - Contract {random.randint(10000, 99999)}",
                f"Membership fee - Member {random.randint(1000, 9999)}",
            ]
        ),
        "mandateId": f"MNDT-{random.randint(2024, 2026)}-{random.randint(10000, 99999)}",
        "creditorSchemeId": f"{creditor['country']}{random.randint(10, 99)}ZZZ{random.randint(10000000, 99999999)}",
        "sequenceType": random.choice(SEQUENCE_TYPES),
        "debtor": {
            "name": debtor["name"],
            "account": {"iban": debtor["iban"]},
        },
        "creditor": {
            "name": creditor["name"],
            "account": {"iban": creditor["iban"]},
        },
        "debtorAgent": {"bic": debtor_bank["bic"]},
        "creditorAgent": {"bic": creditor_bank["bic"]},
    }


# ---------------------------------------------------------------------------
# Type distribution weights
# ---------------------------------------------------------------------------

TYPE_GENERATORS = {
    "pacs.008": generate_pacs008,
    "pacs.009": generate_pacs009,
    "pacs.004": None,  # needs existing UETRs
    "pain.001": generate_pain001,
    "pain.008": generate_pain008,
}

TYPE_WEIGHTS = {
    "pacs.008": 40,  # most common
    "pacs.009": 15,
    "pacs.004": 15,
    "pain.001": 15,
    "pain.008": 15,
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Generate random ISO 20022 payments via the REST API"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=20,
        help="Number of payments to create (default: 20)",
    )
    parser.add_argument(
        "--type",
        choices=list(TYPE_WEIGHTS.keys()),
        help="Generate only this payment type",
    )
    parser.add_argument(
        "--api",
        default="http://localhost:8000",
        help="Base URL of the running API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="Delay between requests in seconds (default: 0.1)",
    )
    args = parser.parse_args()

    api_url = args.api.rstrip("/")
    payments_url = f"{api_url}/api/payments"

    # Verify the API is running
    try:
        resp = requests.get(f"{api_url}/api/health", timeout=5)
        health = resp.json()
        if health.get("status") != "healthy":
            print(f"API is not healthy: {health}")
            sys.exit(1)
        print(f"API: {api_url} (healthy)")
    except requests.ConnectionError:
        print(f"ERROR: Cannot connect to API at {api_url}")
        print("Make sure the backend is running: uvicorn app.main:app --port 8000")
        sys.exit(1)

    # Determine type distribution
    if args.type:
        types = [args.type] * args.count
    else:
        type_list = list(TYPE_WEIGHTS.keys())
        weights = [TYPE_WEIGHTS[t] for t in type_list]
        types = random.choices(type_list, weights=weights, k=args.count)

    # Collect UETRs as we create them (needed for pacs.004 returns)
    created_uetrs = []
    success = 0
    errors = 0

    print(f"Generating {args.count} payments...")
    print()

    type_counts = {}
    for msg_type in types:
        type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
    for t, c in sorted(type_counts.items()):
        label = {
            "pacs.008": "Customer Credit Transfer",
            "pacs.009": "Bank-to-Bank Transfer",
            "pacs.004": "Payment Return",
            "pain.001": "Payment Initiation",
            "pain.008": "Direct Debit",
        }.get(t, t)
        print(f"  {t} ({label}): {c}")
    print()

    for i, msg_type in enumerate(types, 1):
        try:
            # Generate the payload
            if msg_type == "pacs.004":
                payload = generate_pacs004(created_uetrs)
            elif msg_type == "pacs.008":
                payload = generate_pacs008()
            elif msg_type == "pacs.009":
                payload = generate_pacs009()
            elif msg_type == "pain.001":
                payload = generate_pain001()
            elif msg_type == "pain.008":
                payload = generate_pain008()
            else:
                continue

            # POST to the API
            resp = requests.post(
                payments_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            if resp.status_code == 200:
                result = resp.json()
                uetr = result.get("uetr", "?")
                created_uetrs.append(uetr)
                label = result.get("messageTypeLabel", msg_type)
                print(
                    f"  [{i}/{args.count}] {msg_type} | {label} | {uetr[:12]}... | {payload.get('currency')} {payload.get('amount'):,.2f}"
                )
                success += 1
            else:
                detail = resp.json().get("detail", resp.text[:100])
                print(f"  [{i}/{args.count}] ERROR {resp.status_code}: {detail}")
                errors += 1

        except Exception as e:
            print(f"  [{i}/{args.count}] ERROR: {e}")
            errors += 1

        if args.delay > 0:
            time.sleep(args.delay)

    print()
    print(f"Done! Created {success} payments, {errors} errors.")
    print(
        f"View them at: {api_url.replace('localhost:8000', 'localhost:5173')}/payments"
    )


if __name__ == "__main__":
    main()
