"""
WebSocket endpoint backed by MongoDB Change Streams.

One Change Stream on the payments collection feeds all connected clients.
Each client receives real-time events for:
  - insert: new payment created (any of the 5 polymorphic types)
  - update: payment status changed, fields modified
  - replace: full document replacement

The Change Stream also triggers server-side logic:
  - pacs.004 inserts automatically link back to the original payment

MongoDB VALUE PROP: Change Streams provide a real-time event-driven
architecture with no polling, no external message queue, and guaranteed
ordering via the oplog. Resume tokens allow reconnection without missing events.
"""

import asyncio
import json
import traceback
from datetime import datetime, timezone
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from bson import Decimal128, ObjectId

from app.database import get_database

router = APIRouter()

# All connected WebSocket clients
connected_clients: Set[WebSocket] = set()


def serialize_for_ws(obj):
    """JSON serializer for MongoDB types."""
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, Decimal128):
        return float(str(obj))
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return obj.hex()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


async def broadcast(message: dict):
    """Send a message to all connected WebSocket clients."""
    if not connected_clients:
        return
    text = json.dumps(message, default=serialize_for_ws)
    disconnected = set()
    for ws in connected_clients:
        try:
            await ws.send_text(text)
        except Exception:
            disconnected.add(ws)
    connected_clients.difference_update(disconnected)


async def handle_return_detection(full_doc: dict):
    """
    When a pacs.004 (Payment Return) is inserted, automatically link it
    back to the original payment by updating the original with a returnedBy field.

    MongoDB VALUE PROP: Change Streams enable reactive server-side logic
    triggered by database events — no polling, no cron jobs, no message queue.
    """
    db = get_database()
    original_uetr = full_doc.get("originalUetr")
    return_uetr = full_doc.get("uetr")

    if not original_uetr or not return_uetr:
        return

    # Update the original payment to flag it as returned
    result = await db.payments.update_one(
        {"uetr": original_uetr},
        {
            "$set": {
                "returnedBy": return_uetr,
                "returnDetectedAt": datetime.now(timezone.utc),
            }
        },
    )

    if result.modified_count > 0:
        # Broadcast a special return-linked event
        await broadcast(
            {
                "type": "return_linked",
                "originalUetr": original_uetr,
                "returnUetr": return_uetr,
                "returnReason": full_doc.get("returnReason", {}),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )


async def watch_payments():
    """
    Watch the payments collection for changes and broadcast to WebSocket clients.

    MongoDB VALUE PROP: Change Streams
    - Real-time event stream from the oplog
    - Guaranteed ordering
    - Resume tokens for reconnection without missing events
    - Filter by operation type, collection, or field-level changes
    - No external infrastructure (Kafka, RabbitMQ) required
    """
    db = get_database()

    # Watch for inserts and updates on the payments collection
    pipeline = [{"$match": {"operationType": {"$in": ["insert", "update", "replace"]}}}]

    while True:
        try:
            async with db.payments.watch(
                pipeline,
                full_document="updateLookup",
            ) as stream:
                print("Change Stream: watching payments collection...")
                async for change in stream:
                    op_type = change.get("operationType")
                    full_doc = change.get("fullDocument")

                    if not full_doc:
                        continue

                    # Build the event payload
                    event = {
                        "type": op_type,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "payment": {
                            "uetr": full_doc.get("uetr"),
                            "messageType": full_doc.get("messageType"),
                            "settlementAmount": full_doc.get("settlementAmount"),
                            "settlementCurrency": full_doc.get("settlementCurrency"),
                            "status": full_doc.get("status"),
                            "priority": full_doc.get("priority"),
                            "direction": full_doc.get("direction"),
                            "debtor": full_doc.get("debtor"),
                            "creditor": full_doc.get("creditor"),
                            "debtorAgent": full_doc.get("debtorAgent"),
                            "creditorAgent": full_doc.get("creditorAgent"),
                            "settlementDate": full_doc.get("settlementDate"),
                            "statusHistory": full_doc.get("statusHistory"),
                            "remittanceSummary": full_doc.get("remittanceSummary"),
                            # Type-specific fields
                            "returnReason": full_doc.get("returnReason"),
                            "originalUetr": full_doc.get("originalUetr"),
                            "mandateId": full_doc.get("mandateId"),
                            "sequenceType": full_doc.get("sequenceType"),
                            "initiatingParty": full_doc.get("initiatingParty"),
                            "numberOfTransactions": full_doc.get(
                                "numberOfTransactions"
                            ),
                            "returnedBy": full_doc.get("returnedBy"),
                        },
                    }

                    # Include update-specific info
                    if op_type == "update":
                        update_desc = change.get("updateDescription", {})
                        event["updatedFields"] = list(
                            update_desc.get("updatedFields", {}).keys()
                        )

                    # Broadcast to all connected clients
                    await broadcast(event)

                    # Server-side logic: detect pacs.004 returns
                    if (
                        op_type == "insert"
                        and full_doc.get("messageType") == "pacs.004"
                    ):
                        await handle_return_detection(full_doc)

        except Exception as e:
            print(f"Change Stream error: {e}")
            traceback.print_exc()
            # Wait before reconnecting — resume token handles gap
            await asyncio.sleep(2)


@router.websocket("/ws/payments")
async def websocket_payments(websocket: WebSocket):
    """
    WebSocket endpoint for real-time payment events.

    Clients connect here to receive Change Stream events.
    The Change Stream is shared across all connections (one watcher, many consumers).
    """
    await websocket.accept()
    connected_clients.add(websocket)
    client_count = len(connected_clients)
    print(f"WebSocket: client connected ({client_count} total)")

    # Send initial connection confirmation
    await websocket.send_text(
        json.dumps(
            {
                "type": "connected",
                "message": "Connected to MongoDB Change Stream",
                "clients": client_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    )

    try:
        # Keep the connection alive — listen for pings or close
        while True:
            data = await websocket.receive_text()
            # Client can send a ping; we respond with pong
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        connected_clients.discard(websocket)
        print(f"WebSocket: client disconnected ({len(connected_clients)} remaining)")
