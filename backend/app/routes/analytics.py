from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta, timezone

from app.database import get_database
from app.utils.helpers import serialize_doc

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard():
    """
    MongoDB VALUE PROP: Aggregation Framework
    Complex analytics computed server-side with MongoDB's aggregation pipeline.
    No need to pull raw data to the application layer.
    """
    db = get_database()

    # Total payments count and amount
    total_pipeline = [
        {
            "$group": {
                "_id": None,
                "totalCount": {"$sum": 1},
                "totalAmount": {"$sum": {"$toDouble": "$settlementAmount"}},
                "avgAmount": {"$avg": {"$toDouble": "$settlementAmount"}},
            }
        }
    ]

    # Status distribution
    status_pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]

    # Currency distribution
    currency_pipeline = [
        {
            "$group": {
                "_id": "$settlementCurrency",
                "count": {"$sum": 1},
                "totalAmount": {"$sum": {"$toDouble": "$settlementAmount"}},
            }
        },
        {"$sort": {"totalAmount": -1}},
    ]

    # Recent activity (last 30 days by day)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    daily_pipeline = [
        {"$match": {"createdAt": {"$gte": thirty_days_ago}}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$createdAt"}},
                "count": {"$sum": 1},
                "volume": {"$sum": {"$toDouble": "$settlementAmount"}},
            }
        },
        {"$sort": {"_id": 1}},
    ]

    totals = await db.payments.aggregate(total_pipeline).to_list(1)
    statuses = await db.payments.aggregate(status_pipeline).to_list(10)
    currencies = await db.payments.aggregate(currency_pipeline).to_list(20)
    daily = await db.payments.aggregate(daily_pipeline).to_list(30)

    # Investigation stats
    inv_pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    inv_stats = await db.investigations.aggregate(inv_pipeline).to_list(10)

    return {
        "summary": totals[0]
        if totals
        else {"totalCount": 0, "totalAmount": 0, "avgAmount": 0},
        "statusDistribution": [
            {"status": s["_id"], "count": s["count"]} for s in statuses
        ],
        "currencyDistribution": [
            {"currency": c["_id"], "count": c["count"], "totalAmount": c["totalAmount"]}
            for c in currencies
        ],
        "dailyActivity": [
            {"date": d["_id"], "count": d["count"], "volume": d["volume"]}
            for d in daily
        ],
        "investigationStats": [
            {"status": i["_id"], "count": i["count"]} for i in inv_stats
        ],
    }


@router.get("/top-corridors")
async def get_top_corridors(limit: int = Query(10, ge=1, le=50)):
    """
    MongoDB VALUE PROP: Aggregation Pipeline
    Compute top payment corridors (country pairs) entirely server-side.
    """
    db = get_database()
    pipeline = [
        {
            "$group": {
                "_id": {
                    "from": "$debtor.address.country",
                    "to": "$creditor.address.country",
                },
                "count": {"$sum": 1},
                "totalVolume": {"$sum": {"$toDouble": "$settlementAmount"}},
                "avgAmount": {"$avg": {"$toDouble": "$settlementAmount"}},
            }
        },
        {"$sort": {"totalVolume": -1}},
        {"$limit": limit},
        {
            "$project": {
                "corridor": {
                    "$concat": [
                        {"$ifNull": ["$_id.from", "??"]},
                        " → ",
                        {"$ifNull": ["$_id.to", "??"]},
                    ]
                },
                "fromCountry": "$_id.from",
                "toCountry": "$_id.to",
                "count": 1,
                "totalVolume": 1,
                "avgAmount": 1,
            }
        },
    ]

    corridors = await db.payments.aggregate(pipeline).to_list(limit)
    return {"data": corridors}


@router.get("/agent-activity")
async def get_agent_activity():
    """
    MongoDB VALUE PROP: Faceted Aggregation
    Multiple aggregation results in one pipeline using $facet.
    """
    db = get_database()
    pipeline = [
        {
            "$facet": {
                "topDebtorAgents": [
                    {
                        "$group": {
                            "_id": "$debtorAgent.bic",
                            "count": {"$sum": 1},
                            "volume": {"$sum": {"$toDouble": "$settlementAmount"}},
                        }
                    },
                    {"$sort": {"volume": -1}},
                    {"$limit": 10},
                ],
                "topCreditorAgents": [
                    {
                        "$group": {
                            "_id": "$creditorAgent.bic",
                            "count": {"$sum": 1},
                            "volume": {"$sum": {"$toDouble": "$settlementAmount"}},
                        }
                    },
                    {"$sort": {"volume": -1}},
                    {"$limit": 10},
                ],
                "settlementMethods": [
                    {"$group": {"_id": "$settlementMethod", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                ],
            }
        }
    ]

    result = await db.payments.aggregate(pipeline).to_list(1)
    return result[0] if result else {}


@router.get("/processing-times")
async def get_processing_times():
    """
    MongoDB VALUE PROP: Complex Computations on Embedded Data
    Calculate processing times from embedded statusHistory arrays.
    No JOINs to a separate status_log table.
    """
    db = get_database()
    pipeline = [
        {"$match": {"status": "ACSC", "statusHistory": {"$exists": True, "$ne": []}}},
        {
            "$project": {
                "settlementCurrency": 1,
                "processingTimeMs": {
                    "$subtract": [
                        {"$arrayElemAt": ["$statusHistory.timestamp", -1]},
                        {"$arrayElemAt": ["$statusHistory.timestamp", 0]},
                    ]
                },
            }
        },
        {
            "$group": {
                "_id": "$settlementCurrency",
                "avgProcessingMs": {"$avg": "$processingTimeMs"},
                "minProcessingMs": {"$min": "$processingTimeMs"},
                "maxProcessingMs": {"$max": "$processingTimeMs"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"count": -1}},
    ]

    result = await db.payments.aggregate(pipeline).to_list(20)
    return {"data": result}
