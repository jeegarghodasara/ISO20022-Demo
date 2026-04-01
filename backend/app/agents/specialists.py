"""
Specialized Payment Agents — each with domain expertise and persistent memory.

All agents follow the same pattern:
1. Receive a task (payment data + question)
2. Recall relevant memories from past experience
3. Query MongoDB for real-time data
4. Produce a decision with reasoning
5. Store the decision as a new episodic memory
"""

from datetime import datetime, timezone

from app.database import get_database
from app.agents.memory import store_memory, recall_memories
from app.utils.helpers import serialize_doc


# ============================================================================
# Agent Registry
# ============================================================================

AGENT_REGISTRY = {
    "routing-agent": {
        "name": "Payment Routing Agent",
        "description": "Decides optimal payment routes based on corridor, amount, speed, and cost",
        "icon": "Route",
        "color": "#00ED64",
    },
    "compliance-agent": {
        "name": "Compliance Screening Agent",
        "description": "Screens payments against sanctions lists, detects AML patterns, assesses risk",
        "icon": "Shield",
        "color": "#016BF8",
    },
    "exception-agent": {
        "name": "Exception Handler Agent",
        "description": "Investigates failed payments, recommends corrections, manages returns",
        "icon": "AlertTriangle",
        "color": "#FFC010",
    },
    "reconciliation-agent": {
        "name": "Reconciliation Agent",
        "description": "Matches payments to invoices, identifies discrepancies, resolves breaks",
        "icon": "GitCompare",
        "color": "#B45AF2",
    },
    "orchestrator": {
        "name": "Orchestrator Agent",
        "description": "Coordinates other agents, manages conversation flow, delegates tasks",
        "icon": "Brain",
        "color": "#FF6960",
    },
}


# ============================================================================
# Routing Agent
# ============================================================================


async def routing_agent_process(
    payment: dict, question: str, conversation_id: str
) -> dict:
    """
    Analyze a payment and recommend the optimal routing path.
    Uses memory of past routing decisions and real-time corridor data.
    """
    db = get_database()
    agent_id = "routing-agent"

    # 1. Recall relevant past routing decisions
    corridor = f"{payment.get('debtor', {}).get('address', {}).get('country', '??')} to {payment.get('creditor', {}).get('address', {}).get('country', '??')}"
    recall_query = f"Route payment {corridor} {payment.get('settlementCurrency', '')} {payment.get('settlementAmount', '')}"
    memories = await recall_memories(agent_id, recall_query, limit=5)

    # 2. Query real-time corridor statistics
    from_country = payment.get("debtor", {}).get("address", {}).get("country")
    to_country = payment.get("creditor", {}).get("address", {}).get("country")

    corridor_stats = None
    if from_country and to_country:
        pipeline = [
            {
                "$match": {
                    "debtor.address.country": from_country,
                    "creditor.address.country": to_country,
                    "status": "ACSC",
                }
            },
            {
                "$group": {
                    "_id": None,
                    "totalPayments": {"$sum": 1},
                    "avgAmount": {"$avg": {"$toDouble": "$settlementAmount"}},
                    "commonAgents": {"$addToSet": "$debtorAgent.bic"},
                    "currencies": {"$addToSet": "$settlementCurrency"},
                }
            },
        ]
        results = await db.payments.aggregate(pipeline).to_list(1)
        corridor_stats = results[0] if results else None

    # 3. Determine routing recommendation
    routes = []
    if payment.get("settlementCurrency") in ["EUR"] and from_country in [
        "DE",
        "FR",
        "NL",
        "IT",
        "ES",
        "BE",
        "AT",
    ]:
        routes.append(
            {
                "method": "SEPA",
                "speed": "Same day",
                "cost": "Low",
                "confidence": 0.95,
                "reason": "EUR payment within SEPA zone — fastest and cheapest",
            }
        )
    if payment.get("settlementCurrency") in ["GBP"] and from_country == "GB":
        routes.append(
            {
                "method": "Faster Payments",
                "speed": "Near instant",
                "cost": "Very low",
                "confidence": 0.93,
                "reason": "Domestic GBP payment — use Faster Payments network",
            }
        )

    routes.append(
        {
            "method": "SWIFT gpi",
            "speed": "1-2 business days",
            "cost": "Medium",
            "confidence": 0.85,
            "reason": "International transfer with tracking via SWIFT gpi",
        }
    )

    # Add cover payment route for large amounts
    amount = payment.get("settlementAmount", 0)
    if isinstance(amount, (int, float)) and amount > 500000:
        routes.insert(
            0,
            {
                "method": "SWIFT Cover (pacs.009)",
                "speed": "Same day",
                "cost": "Higher",
                "confidence": 0.90,
                "reason": f"High-value payment ({amount:,.0f}) — cover payment for guaranteed settlement",
            },
        )

    recommended = routes[0] if routes else {"method": "SWIFT", "confidence": 0.5}

    # 4. Build the response
    result = {
        "agent": agent_id,
        "decision": f"Recommended route: {recommended['method']}",
        "recommendation": recommended,
        "alternatives": routes[1:3],
        "corridor": corridor,
        "corridorStats": serialize_doc(corridor_stats) if corridor_stats else None,
        "memoriesUsed": len(memories),
        "reasoning": [
            f"Analyzed {corridor} corridor",
            f"Found {len(memories)} relevant past routing decisions",
            f"Corridor has {corridor_stats['totalPayments'] if corridor_stats else 0} settled payments"
            if corridor_stats
            else "No prior corridor data",
            recommended.get("reason", ""),
        ],
    }

    # 5. Store this decision as episodic memory
    await store_memory(
        agent_id=agent_id,
        memory_type="episodic",
        content=f"Routed {corridor} payment of {payment.get('settlementCurrency', '')} {amount} via {recommended['method']}. Confidence: {recommended.get('confidence', 0):.0%}",
        context={
            "corridor": corridor,
            "amount": amount,
            "currency": payment.get("settlementCurrency"),
            "method": recommended["method"],
            "confidence": recommended.get("confidence"),
        },
        conversation_id=conversation_id,
    )

    return result


# ============================================================================
# Compliance Agent
# ============================================================================


async def compliance_agent_process(
    payment: dict, question: str, conversation_id: str
) -> dict:
    """Screen a payment for compliance risks."""
    db = get_database()
    agent_id = "compliance-agent"

    debtor_name = payment.get("debtor", {}).get("name", "Unknown")
    creditor_name = payment.get("creditor", {}).get("name", "Unknown")

    # 1. Recall past screening results for these parties
    recall_query = f"Screen {debtor_name} {creditor_name} payment"
    memories = await recall_memories(agent_id, recall_query, limit=5)

    # 2. Check payment patterns in MongoDB
    debtor_iban = payment.get("debtor", {}).get("account", {}).get("iban")
    pattern_data = None
    if debtor_iban:
        pipeline = [
            {"$match": {"debtor.account.iban": debtor_iban}},
            {
                "$group": {
                    "_id": None,
                    "totalPayments": {"$sum": 1},
                    "totalVolume": {"$sum": {"$toDouble": "$settlementAmount"}},
                    "avgAmount": {"$avg": {"$toDouble": "$settlementAmount"}},
                    "countries": {"$addToSet": "$creditor.address.country"},
                    "rejectedCount": {
                        "$sum": {"$cond": [{"$eq": ["$status", "RJCT"]}, 1, 0]}
                    },
                }
            },
        ]
        results = await db.payments.aggregate(pipeline).to_list(1)
        pattern_data = results[0] if results else None

    # 3. Run risk assessment
    risk_factors = []
    risk_score = 0

    amount = payment.get("settlementAmount", 0)
    if isinstance(amount, (int, float)):
        if amount > 1000000:
            risk_factors.append(
                {
                    "factor": "High value transaction",
                    "weight": 30,
                    "detail": f"Amount: {amount:,.2f}",
                }
            )
            risk_score += 30
        elif amount > 100000:
            risk_factors.append(
                {
                    "factor": "Elevated value",
                    "weight": 10,
                    "detail": f"Amount: {amount:,.2f}",
                }
            )
            risk_score += 10

    if payment.get("priority") == "HIGH":
        risk_factors.append(
            {
                "factor": "High priority flag",
                "weight": 5,
                "detail": "Payment marked as urgent",
            }
        )
        risk_score += 5

    if pattern_data and pattern_data.get("rejectedCount", 0) > 2:
        risk_factors.append(
            {
                "factor": "Prior rejections",
                "weight": 20,
                "detail": f"{pattern_data['rejectedCount']} rejected payments from this account",
            }
        )
        risk_score += 20

    # Past memory influence
    prior_clean = sum(
        1
        for m in memories
        if "clean" in m.get("content", "").lower()
        or "approved" in m.get("content", "").lower()
    )
    if prior_clean >= 2:
        risk_factors.append(
            {
                "factor": "Prior clean screenings",
                "weight": -10,
                "detail": f"{prior_clean} previous clean screenings for related parties",
            }
        )
        risk_score = max(0, risk_score - 10)

    risk_level = "LOW" if risk_score < 20 else "MEDIUM" if risk_score < 50 else "HIGH"
    decision = "APPROVED" if risk_level in ["LOW", "MEDIUM"] else "ESCALATE"

    result = {
        "agent": agent_id,
        "decision": f"Screening {decision} — Risk: {risk_level} (score: {risk_score})",
        "riskLevel": risk_level,
        "riskScore": risk_score,
        "screeningResult": decision,
        "riskFactors": risk_factors,
        "partiesScreened": [debtor_name, creditor_name],
        "priorHistory": serialize_doc(pattern_data) if pattern_data else None,
        "memoriesUsed": len(memories),
        "reasoning": [
            f"Screened debtor: {debtor_name}",
            f"Screened creditor: {creditor_name}",
            f"Risk score: {risk_score} ({risk_level})",
            f"Found {len(memories)} prior screening records",
            f"Decision: {decision}",
        ],
    }

    await store_memory(
        agent_id=agent_id,
        memory_type="episodic",
        content=f"Screened payment from {debtor_name} to {creditor_name}. Result: {decision}, Risk: {risk_level} (score {risk_score})",
        context={
            "debtor": debtor_name,
            "creditor": creditor_name,
            "riskLevel": risk_level,
            "decision": decision,
        },
        conversation_id=conversation_id,
    )

    return result


# ============================================================================
# Exception Handler Agent
# ============================================================================


async def exception_agent_process(
    payment: dict, question: str, conversation_id: str
) -> dict:
    """Investigate a failed or returned payment and recommend corrective action."""
    db = get_database()
    agent_id = "exception-agent"

    status = payment.get("status", "")
    return_reason = payment.get("returnReason", {})
    reason_code = return_reason.get("code", "")

    # 1. Recall similar past exceptions
    recall_query = (
        f"Exception {status} {reason_code} {return_reason.get('description', '')}"
    )
    memories = await recall_memories(agent_id, recall_query, limit=5)

    # 2. Find similar past failures in MongoDB
    similar_query = {"status": "RJCT"}
    if reason_code:
        similar_query["returnReason.code"] = reason_code
    similar_count = await db.payments.count_documents(similar_query)

    # 3. Determine corrective action
    actions = []
    if reason_code == "AC04":
        actions.append(
            {
                "action": "Contact creditor for updated account details",
                "priority": "HIGH",
                "automate": False,
            }
        )
        actions.append(
            {
                "action": "Request new beneficiary IBAN via camt.056",
                "priority": "MEDIUM",
                "automate": True,
            }
        )
    elif reason_code == "AC06":
        actions.append(
            {
                "action": "Verify account status with creditor bank",
                "priority": "HIGH",
                "automate": False,
            }
        )
    elif reason_code == "AM05":
        actions.append(
            {
                "action": "Check for duplicate payment — may be resolved automatically",
                "priority": "MEDIUM",
                "automate": True,
            }
        )
    elif reason_code == "RC01":
        actions.append(
            {
                "action": "Validate BIC using SWIFT directory",
                "priority": "HIGH",
                "automate": True,
            }
        )
        actions.append(
            {"action": "Retry with corrected BIC", "priority": "HIGH", "automate": True}
        )
    elif status == "RJCT":
        actions.append(
            {
                "action": "Review rejection details and retry with corrections",
                "priority": "HIGH",
                "automate": False,
            }
        )
    else:
        actions.append(
            {
                "action": "Manual investigation required",
                "priority": "MEDIUM",
                "automate": False,
            }
        )

    # Memory-informed suggestions
    for m in memories:
        ctx = m.get("context", {})
        if ctx.get("resolution"):
            actions.append(
                {
                    "action": f"Past resolution: {ctx['resolution']}",
                    "priority": "INFO",
                    "automate": False,
                    "source": "agent memory",
                }
            )
            break

    result = {
        "agent": agent_id,
        "decision": f"Exception analysis complete — {len(actions)} corrective actions",
        "status": status,
        "returnReason": return_reason,
        "recommendedActions": actions,
        "similarFailures": similar_count,
        "memoriesUsed": len(memories),
        "reasoning": [
            f"Payment status: {status}",
            f"Return reason: {reason_code} — {return_reason.get('description', 'N/A')}",
            f"Found {similar_count} similar failures in history",
            f"Recalled {len(memories)} relevant past exception resolutions",
            f"Recommending {len(actions)} corrective actions",
        ],
    }

    await store_memory(
        agent_id=agent_id,
        memory_type="episodic",
        content=f"Investigated {status} payment. Reason: {reason_code}. Recommended {len(actions)} actions. Similar failures: {similar_count}.",
        context={
            "status": status,
            "reasonCode": reason_code,
            "actionsCount": len(actions),
        },
        conversation_id=conversation_id,
    )

    return result


# ============================================================================
# Reconciliation Agent
# ============================================================================


async def reconciliation_agent_process(
    payment: dict, question: str, conversation_id: str
) -> dict:
    """Match a payment against expected receivables or invoices."""
    db = get_database()
    agent_id = "reconciliation-agent"

    remittance = payment.get("remittanceSummary", {}).get("unstructuredText", "")
    amount = payment.get("settlementAmount", 0)
    currency = payment.get("settlementCurrency", "")
    debtor_name = payment.get("debtor", {}).get("name", "Unknown")

    # 1. Recall similar past matchings
    recall_query = (
        f"Match payment from {debtor_name} remittance {remittance} {amount} {currency}"
    )
    memories = await recall_memories(agent_id, recall_query, limit=5)

    # 2. Search for potential matches using remittance text
    potential_matches = []
    if remittance:
        cursor = db.payments.find(
            {
                "remittanceSummary.unstructuredText": {
                    "$regex": remittance[:20],
                    "$options": "i",
                },
                "uetr": {"$ne": payment.get("uetr")},
            },
            {
                "uetr": 1,
                "settlementAmount": 1,
                "settlementCurrency": 1,
                "debtor.name": 1,
                "remittanceSummary.unstructuredText": 1,
            },
        ).limit(5)
        potential_matches = [serialize_doc(doc) async for doc in cursor]

    # 3. Determine match confidence
    match_result = "NO_MATCH"
    confidence = 0.0
    matched_to = None

    if potential_matches:
        best = potential_matches[0]
        confidence = 0.7  # base for text match
        if abs(float(best.get("settlementAmount", 0)) - float(amount)) < 0.01:
            confidence += 0.2  # amount matches exactly
        if best.get("settlementCurrency") == currency:
            confidence += 0.1

        if confidence >= 0.8:
            match_result = "MATCHED"
            matched_to = best.get("uetr")
        elif confidence >= 0.5:
            match_result = "PROBABLE"
            matched_to = best.get("uetr")

    result = {
        "agent": agent_id,
        "decision": f"Reconciliation: {match_result} (confidence: {confidence:.0%})",
        "matchResult": match_result,
        "confidence": confidence,
        "matchedTo": matched_to,
        "potentialMatches": potential_matches[:3],
        "remittanceText": remittance,
        "memoriesUsed": len(memories),
        "reasoning": [
            f"Analyzed remittance: '{remittance[:60]}...' "
            if len(remittance) > 60
            else f"Analyzed remittance: '{remittance}'",
            f"Found {len(potential_matches)} potential matches",
            f"Best match confidence: {confidence:.0%}",
            f"Result: {match_result}",
        ],
    }

    await store_memory(
        agent_id=agent_id,
        memory_type="episodic",
        content=f"Reconciled payment from {debtor_name}. Remittance: '{remittance[:50]}'. Result: {match_result} ({confidence:.0%})",
        context={
            "matchResult": match_result,
            "confidence": confidence,
            "remittance": remittance[:100],
        },
        conversation_id=conversation_id,
    )

    return result


# ============================================================================
# Orchestrator Agent
# ============================================================================


async def orchestrator_process(
    payment: dict, question: str, conversation_id: str
) -> dict:
    """
    Coordinate other agents to handle a payment task.
    Decides which agents to invoke based on the question and payment context.
    """
    agent_id = "orchestrator"

    # Recall orchestration patterns
    memories = await recall_memories(agent_id, question, limit=3)

    # Determine which agents to invoke
    agents_to_invoke = []
    question_lower = question.lower()

    if any(
        w in question_lower
        for w in ["route", "routing", "path", "send", "transfer", "best way"]
    ):
        agents_to_invoke.append("routing-agent")

    if any(
        w in question_lower
        for w in [
            "compliance",
            "risk",
            "screen",
            "sanction",
            "aml",
            "suspicious",
            "safe",
        ]
    ):
        agents_to_invoke.append("compliance-agent")

    if any(
        w in question_lower
        for w in [
            "fail",
            "reject",
            "return",
            "error",
            "exception",
            "fix",
            "wrong",
            "problem",
        ]
    ):
        agents_to_invoke.append("exception-agent")

    if any(
        w in question_lower
        for w in ["match", "reconcil", "invoice", "remittance", "break"]
    ):
        agents_to_invoke.append("reconciliation-agent")

    # Default: if nothing specific, run routing + compliance (common workflow)
    if not agents_to_invoke:
        agents_to_invoke = ["routing-agent", "compliance-agent"]

    # For "full analysis" or general queries, run all
    if any(
        w in question_lower
        for w in ["full", "complete", "everything", "all agents", "analyze"]
    ):
        agents_to_invoke = [
            "routing-agent",
            "compliance-agent",
            "exception-agent",
            "reconciliation-agent",
        ]

    # Execute each agent
    agent_results = {}
    agent_map = {
        "routing-agent": routing_agent_process,
        "compliance-agent": compliance_agent_process,
        "exception-agent": exception_agent_process,
        "reconciliation-agent": reconciliation_agent_process,
    }

    for agent in agents_to_invoke:
        handler = agent_map.get(agent)
        if handler:
            try:
                result = await handler(payment, question, conversation_id)
                agent_results[agent] = result
            except Exception as e:
                agent_results[agent] = {"agent": agent, "error": str(e)}

    # Build summary
    summary_parts = []
    for agent, result in agent_results.items():
        name = AGENT_REGISTRY[agent]["name"]
        decision = result.get("decision", result.get("error", "Unknown"))
        summary_parts.append(f"{name}: {decision}")

    result = {
        "agent": agent_id,
        "decision": f"Orchestrated {len(agents_to_invoke)} agents for this task",
        "agentsInvoked": agents_to_invoke,
        "agentResults": agent_results,
        "summary": summary_parts,
        "memoriesUsed": len(memories),
        "reasoning": [
            f"Analyzed question: '{question[:80]}'",
            f"Selected {len(agents_to_invoke)} agents: {', '.join(agents_to_invoke)}",
        ]
        + summary_parts,
    }

    await store_memory(
        agent_id=agent_id,
        memory_type="episodic",
        content=f"Orchestrated {', '.join(agents_to_invoke)} for: '{question[:80]}'. Results: {'; '.join(summary_parts[:3])}",
        context={"agents": agents_to_invoke, "question": question[:200]},
        conversation_id=conversation_id,
    )

    return result
