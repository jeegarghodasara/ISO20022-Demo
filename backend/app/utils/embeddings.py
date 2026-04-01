"""
Embedding utilities using MongoDB Atlas AI endpoint with Voyage Finance model.

Calls https://ai.mongodb.com/v1/embeddings (OpenAI-compatible API)
with the voyage-finance-2 model -- purpose-built for financial data.

Generates text embeddings for payment documents to enable:
1. Natural language payment search
2. Similar transaction / anomaly detection
3. Smart remittance matching
"""

import os
import requests
from typing import List, Optional
from app.config import settings

ATLAS_AI_URL = "https://ai.mongodb.com/v1/embeddings"
EMBEDDING_MODEL = "voyage-finance-2"
EMBEDDING_DIMENSIONS = 1024


def _get_api_key() -> str:
    key = settings.voyage_api_key or os.getenv("VOYAGE_API_KEY", "")
    if not key:
        raise RuntimeError(
            "VOYAGE_API_KEY environment variable is not set. "
            "This key is used to authenticate with the MongoDB Atlas AI endpoint."
        )
    return key


def _call_atlas_embeddings(
    texts: List[str], input_type: str = "document"
) -> List[List[float]]:
    """Call the MongoDB Atlas AI embedding endpoint."""
    api_key = _get_api_key()
    response = requests.post(
        ATLAS_AI_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "input": texts,
            "model": EMBEDDING_MODEL,
            "input_type": input_type,
        },
        timeout=30,
    )
    if response.status_code != 200:
        detail = response.json().get("detail", response.text[:200])
        raise RuntimeError(f"Atlas AI API error ({response.status_code}): {detail}")

    data = response.json()
    # OpenAI-compatible response: data[].embedding
    embeddings = [item["embedding"] for item in data["data"]]
    return embeddings


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a batch of texts (for indexing documents)."""
    return _call_atlas_embeddings(texts, input_type="document")


def embed_query(text: str) -> List[float]:
    """Embed a single query text (for searching)."""
    results = _call_atlas_embeddings([text], input_type="query")
    return results[0]


def payment_to_text(payment: dict) -> str:
    """
    Convert a payment document to a searchable text representation.
    This is what gets embedded for vector search.
    """
    parts = []

    # Message type context
    type_labels = {
        "pacs.008": "Customer Credit Transfer",
        "pacs.009": "Bank-to-Bank Transfer",
        "pacs.004": "Payment Return",
        "pain.001": "Payment Initiation",
        "pain.008": "Direct Debit Initiation",
    }
    msg_type = payment.get("messageType", "")
    parts.append(f"Payment type: {type_labels.get(msg_type, msg_type)}")

    # Amount and currency
    amount = payment.get("settlementAmount")
    currency = payment.get("settlementCurrency", "")
    if amount is not None:
        parts.append(f"Amount: {amount} {currency}")

    # Status
    status_labels = {
        "ACTC": "Technical Validation OK",
        "ACCP": "Accepted by Customer",
        "ACSP": "Processing",
        "ACSC": "Settled Successfully",
        "RJCT": "Rejected",
        "PDNG": "Pending",
        "CANC": "Cancelled",
    }
    status = payment.get("status", "")
    parts.append(f"Status: {status_labels.get(status, status)}")

    # Priority
    priority = payment.get("priority", "")
    if priority == "HIGH":
        parts.append("Priority: High/Urgent")
    else:
        parts.append("Priority: Normal")

    # Debtor
    debtor = payment.get("debtor", {})
    if debtor.get("name"):
        parts.append(f"Sender: {debtor['name']}")
    debtor_country = debtor.get("address", {}).get("country", "")
    if debtor_country:
        parts.append(f"Sender country: {debtor_country}")

    # Creditor
    creditor = payment.get("creditor", {})
    if creditor.get("name"):
        parts.append(f"Receiver: {creditor['name']}")
    creditor_country = creditor.get("address", {}).get("country", "")
    if creditor_country:
        parts.append(f"Receiver country: {creditor_country}")

    # Corridor
    if debtor_country and creditor_country:
        parts.append(f"Corridor: {debtor_country} to {creditor_country}")

    # Agents
    debtor_agent = payment.get("debtorAgent", {})
    if debtor_agent.get("bic"):
        parts.append(
            f"Sender bank: {debtor_agent.get('name', '')} ({debtor_agent['bic']})"
        )
    creditor_agent = payment.get("creditorAgent", {})
    if creditor_agent.get("bic"):
        parts.append(
            f"Receiver bank: {creditor_agent.get('name', '')} ({creditor_agent['bic']})"
        )

    # Remittance info
    remit = payment.get("remittanceSummary", {})
    if remit.get("unstructuredText"):
        parts.append(f"Remittance: {remit['unstructuredText']}")

    # Type-specific fields
    if msg_type == "pacs.004":
        reason = payment.get("returnReason", {})
        if reason.get("code"):
            parts.append(f"Return reason: {reason['code']}")
        if reason.get("description"):
            parts.append(f"Return description: {reason['description']}")

    if msg_type == "pain.008":
        mandate = payment.get("mandateId", "")
        if mandate:
            parts.append(f"Mandate: {mandate}")
        seq = payment.get("sequenceType", "")
        if seq:
            seq_labels = {
                "FRST": "First",
                "RCUR": "Recurring",
                "FNAL": "Final",
                "OOFF": "One-Off",
            }
            parts.append(f"Sequence: {seq_labels.get(seq, seq)}")

    return ". ".join(parts)


def remittance_to_text(payment: dict) -> str:
    """
    Convert remittance information to text for matching.
    Focuses on invoice/reference data for the smart matching use case.
    """
    parts = []

    remit = payment.get("remittanceSummary", {})
    if remit.get("unstructuredText"):
        parts.append(remit["unstructuredText"])

    # Include debtor/creditor names for context
    debtor = payment.get("debtor", {})
    if debtor.get("name"):
        parts.append(f"From: {debtor['name']}")
    creditor = payment.get("creditor", {})
    if creditor.get("name"):
        parts.append(f"To: {creditor['name']}")

    amount = payment.get("settlementAmount")
    currency = payment.get("settlementCurrency", "")
    if amount:
        parts.append(f"Amount: {amount} {currency}")

    return ". ".join(parts) if parts else "No remittance information"
