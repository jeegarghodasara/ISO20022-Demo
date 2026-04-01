"""
Generate vector embeddings for existing payment documents.

This script reads all payments from MongoDB, generates text representations,
creates embeddings via Voyage AI, and stores them back in the payment documents.

Usage:
    python scripts/generate_embeddings.py

Requires:
    VOYAGE_API_KEY environment variable
    MONGODB_URI environment variable (defaults to localhost)
"""

import os
import sys
import time

from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "iso20022_payments")
BATCH_SIZE = 20  # Voyage AI batch limit


def main():
    from app.utils.embeddings import (
        embed_texts,
        payment_to_text,
        remittance_to_text,
        EMBEDDING_MODEL,
        EMBEDDING_DIMENSIONS,
    )

    client = MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]

    print(f"Connected to: {MONGODB_URI}")
    print(f"Database: {DATABASE_NAME}")
    print(f"Embedding model: {EMBEDDING_MODEL} ({EMBEDDING_DIMENSIONS} dimensions)")
    print()

    # Count payments
    total = db.payments.count_documents({})
    already_embedded = db.payments.count_documents({"embedding": {"$exists": True}})
    to_embed = db.payments.count_documents({"embedding": {"$exists": False}})

    print(f"Total payments: {total}")
    print(f"Already embedded: {already_embedded}")
    print(f"To embed: {to_embed}")
    print()

    if to_embed == 0:
        print("All payments already have embeddings. Nothing to do.")
        # Offer to re-embed
        if already_embedded > 0:
            response = input("Re-generate all embeddings? (y/N): ").strip().lower()
            if response != "y":
                return
            to_embed = total
            cursor = db.payments.find({})
        else:
            return
    else:
        cursor = db.payments.find({"embedding": {"$exists": False}})

    # Process in batches
    batch = []
    batch_texts = []
    batch_remittance_texts = []
    processed = 0
    errors = 0

    print(f"Generating embeddings in batches of {BATCH_SIZE}...")
    print()

    for doc in cursor:
        # Generate text representations
        payment_text = payment_to_text(doc)
        remittance_text = remittance_to_text(doc)

        batch.append(doc)
        batch_texts.append(payment_text)
        batch_remittance_texts.append(remittance_text)

        if len(batch) >= BATCH_SIZE:
            processed += process_batch(
                db, batch, batch_texts, batch_remittance_texts, processed, to_embed
            )
            batch = []
            batch_texts = []
            batch_remittance_texts = []
            # Rate limiting - be respectful to the API
            time.sleep(0.5)

    # Process remaining
    if batch:
        processed += process_batch(
            db, batch, batch_texts, batch_remittance_texts, processed, to_embed
        )

    print()
    print(f"Done! Embedded {processed} payments.")
    print(f"Errors: {errors}")

    # Verify
    embedded_count = db.payments.count_documents({"embedding": {"$exists": True}})
    print(f"Total payments with embeddings: {embedded_count}/{total}")

    client.close()


def process_batch(db, batch, texts, remittance_texts, processed_so_far, total):
    """Embed a batch and write back to MongoDB."""
    from app.utils.embeddings import embed_texts

    try:
        # Generate payment embeddings
        embeddings = embed_texts(texts)
        # Generate remittance embeddings
        remittance_embeddings = embed_texts(remittance_texts)

        # Bulk update
        updates = []
        for i, doc in enumerate(batch):
            updates.append(
                UpdateOne(
                    {"_id": doc["_id"]},
                    {
                        "$set": {
                            "embedding": embeddings[i],
                            "embeddingText": texts[i],
                            "remittanceEmbedding": remittance_embeddings[i],
                            "remittanceEmbeddingText": remittance_texts[i],
                        }
                    },
                )
            )

        result = db.payments.bulk_write(updates)
        count = result.modified_count
        print(
            f"  Batch complete: {processed_so_far + count}/{total} "
            f"({(processed_so_far + count) / total * 100:.0f}%)"
        )
        return count

    except Exception as e:
        print(f"  ERROR in batch: {e}")
        return 0


if __name__ == "__main__":
    main()
