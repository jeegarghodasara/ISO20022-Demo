# MongoDB for Payments — End-to-End Demo Script

This script walks through a 15–20 minute live demo showcasing MongoDB's capabilities for ISO 20022 payment processing, AI-powered search, multi-agent architecture, and real-time event streaming.

**Prerequisites:**
- Backend running: `cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000`
- Frontend running: `cd frontend && npm run dev`
- Database seeded: `python scripts/seed_data.py` (run once)
- Embeddings generated: `python scripts/generate_embeddings.py` (run once)
- Open http://localhost:5173 in your browser

---

## Act 1: Polymorphic Payments (3 minutes)

**Key message:** MongoDB stores 5 structurally different payment types in one collection — no JOINs, no NULLs, no migrations.

### Create two different payment types

1. Navigate to **New Payment** in the sidebar
2. Show the 5 payment type cards — each represents a different ISO 20022 message type
3. Select **Customer Credit Transfer** (pacs.008)
   - Fill in: Amount `50000`, Currency `EUR`, Debtor `John Schmidt`, Creditor `Jane Smith`
   - Point out the **Document Schema Preview** on the right — this is what MongoDB stores
   - Submit the payment
4. Go back to **New Payment**, select **Payment Return** (pacs.004)
   - Point out the **different form fields**: Return Reason Code, Original Payment UETR
   - Fill in the fields (use any UETR from the Payments list)
   - Submit

> **Say:** "Notice how the form changed completely — different fields for different payment types. But both documents go into the same `payments` collection. MongoDB handles the different shapes naturally — no ALTER TABLE, no migration."

### Show the unified list

5. Navigate to **All Payments**
6. Both payments appear in one list — use the **Payment Type** filter to show only Credit Transfers, then only Payment Returns
7. Point out the **MongoDB Query** panel that appears below the filters — it shows the actual `db.payments.find()` query

### Show type-specific detail

8. Click the pacs.004 Payment Return
9. Point out the **Return Details** section (orange) — this section only appears for returns
10. Point out the **MongoDB Polymorphic Document Model** callout explaining this is one read, zero JOINs

---

## Act 2: Real-Time with Change Streams (3 minutes)

**Key message:** MongoDB Change Streams provide real-time event streaming — no Kafka, no polling, no external message queue.

### Setup

Open two browser tabs side by side:
- **Tab 1:** Live Feed (`/live`)
- **Tab 2:** Dashboard (`/`)

### Run the payment generator

In a terminal:
```bash
cd backend && source venv/bin/activate
python scripts/generate_payments.py --count 15 --delay 1
```

### Watch the real-time feed

11. **Tab 1 (Live Feed):** Watch payments slide in one per second
    - Green dots = new inserts, blue dots = updates
    - Each card shows: payment type badge, amount, debtor → creditor, status
    - Point out the connection status indicator and event counter at the top
12. **Tab 2 (Dashboard):** Watch the **Total Payments** and **Total Volume** stat cards tick up
    - The green pulsing Radio icon indicates live data
    - The green banner shows "+N payments since page load"

> **Say:** "One Change Stream on `db.payments.watch()` feeds both the Live Feed and the Dashboard counters via WebSocket. No Kafka, no Debezium, no polling."

### Status tracking demo

13. Open a payment detail page in a new tab
14. Note the green **Live** indicator next to "Status History"
15. In another tab, click **Set ACSC** on the same payment
16. Watch the first tab's status history auto-update without refresh

> **Say:** "The Change Stream detected the status update and pushed it to the browser instantly. In a relational system, you'd need polling or an external event bus."

### Return detection

17. Still on the Live Feed, run: `python scripts/generate_payments.py --count 3 --type pacs.004 --delay 2`
18. Watch the orange "Return Linked" cards appear — the server-side Change Stream handler automatically linked each return to its original payment

---

## Act 3: AI Vector Search (3 minutes)

**Key message:** MongoDB Atlas Vector Search enables semantic search across all polymorphic payment types — same cluster, same query language, no Elasticsearch.

### Navigate to AI Search

19. Go to **AI Search** in the sidebar
20. Note the status bar: model (voyage-4-large), dimensions (1024), coverage (100%)

### Natural Language Search

21. In the **Natural Language** tab, type: `large transfers to Germany that were rejected`
22. Show the results — MongoDB found relevant payments without exact field matching
23. Expand the **MongoDB Vector Search Pipeline** panel
    - Show the `$vectorSearch` aggregation stage with the query vector, index name, and `numCandidates`

> **Say:** "This is a standard MongoDB aggregation pipeline with $vectorSearch as the first stage. Same query language, same cluster — no separate search engine."

### Remittance Matching

24. Switch to the **Remittance Matching** tab
25. Type: `Invoice 3974 from ACME`
26. Show the top result matched to "Payment for invoice INV-3974" at ~80% similarity

> **Say:** "Semantic matching handles typos, abbreviations, and different formats. Exact string matching would miss this."

### Similar Transactions

27. Switch to **Similar Transactions**, paste a UETR from any payment
28. Show structurally similar payments — same corridor, similar amounts, similar patterns

> **Say:** "This is the fraud detection use case — 'show me payments that look like this suspicious one.' One vector search query across the entire polymorphic collection."

---

## Act 4: Multi-Agent Architecture (5 minutes)

**Key message:** MongoDB serves as the complete infrastructure for an AI agent system — memory store, vector database, message bus, and audit log in one.

### Navigate to AI Agents

29. Go to **AI Agents** in the sidebar
30. Show the 5 agent cards — each shows memory count and message count

### Ask the orchestrator

31. Copy a UETR from the Payments page, paste it in the **Payment UETR** field
32. Click the sample question: **"Run a full analysis with all agents"**
33. Walk through the orchestrator's result:
    - "Orchestrated 4 agents for this task"
    - Expand each agent's result:
      - **Routing Agent:** Recommended route (SEPA/SWIFT), speed, cost, confidence percentage
      - **Compliance Agent:** Risk score with breakdown (high value = +30, prior clean screenings = -10)
      - **Exception Agent:** Corrective actions with priority levels
      - **Reconciliation Agent:** Match confidence based on remittance text

> **Say:** "The orchestrator analyzed the question, decided which agents to invoke, and each agent recalled relevant memories via Vector Search, queried MongoDB for real-time data, and produced a decision."

### Multi-turn conversations

34. Now ask a follow-up: `What if I use SWIFT gpi instead?`
35. Point out:
    - Button says "Follow-up (Turn 2)" — context is carried forward
    - The **size progress bar** below: "3.2KB / 10KB"
    - The Turn 1 and Turn 2 results are both visible in the thread

36. Ask another follow-up: `Is there a compliance concern with this route?`
37. Point out the progress bar growing

> **Say:** "The entire multi-turn conversation is one MongoDB document with a turns array. Atomic $push appends each turn. When it hits 10KB, it prompts for a new conversation — like ChatGPT. This prevents unbounded document growth."

### User feedback

38. Click the **thumbs up** button on Turn 1
39. Show the "Recorded" confirmation

> **Say:** "Feedback is stored directly on the conversation turn with atomic $set on a nested array element — `turns.$.feedback`. No separate feedback table."

---

## Act 5: Agent Memory & Observability (3 minutes)

**Key message:** Agents build persistent memory over time using MongoDB — episodic, semantic, and procedural — with vector search for recall.

### Memory Inspector

40. Click the **Routing Agent** card to select it
41. Click **View Memory Inspector** at the bottom
42. Show the episodic memories — each records a past routing decision with context
43. Filter by **episodic** — show individual decisions
44. Filter by **semantic** — may be empty (we'll fix that next)

### Memory Consolidation

45. Scroll to the **MetricsPanel** and click the **Memory Consolidation** tab
46. Click **Run Consolidation**
47. Show the result: "N semantic memories created"
    - Routing: corridor statistics distilled from episodic memories
    - Compliance: risk level patterns
    - Exception: reason code frequencies

48. Go back to Memory Inspector, filter by **semantic**
49. Show the consolidated entries: "Corridor DE to GB: 5 routing decisions. Methods used: SWIFT gpi. Avg confidence: 90%."

> **Say:** "This is like sleep consolidation in the brain. MongoDB aggregation pipelines grouped episodic memories by corridor and distilled them into permanent semantic knowledge. The agent is now smarter for next time."

### Ask again and show memory recall

50. Ask the routing agent another question about a different payment
51. Point out "used N memories" in the result

> **Say:** "The agent just recalled semantic knowledge from its memory using Vector Search — similarity matching with recency and frequency boosting. The more it runs, the better it gets."

### Performance Metrics

52. Click the **Performance** tab in the MetricsPanel
53. Show per-agent stats: invocation counts, avg/max latency, success rates, memories used
54. Point out the overall stats: total invocations, avg latency

> **Say:** "All computed server-side with $facet — one aggregation pipeline computes per-agent stats, overall stats, and recent activity in a single pass."

### Tool Call Audit Trail

55. Click the **Tool Logs** tab
56. Show the audit trail: every `vector_search:recall_memories` and `aggregation:corridor_stats` the agents executed
57. Show the latency for each operation

> **Say:** "For financial compliance, every database operation the agents execute is logged. This is an append-only audit trail with 30-day TTL — MongoDB handles the retention automatically."

---

## Act 6: Dashboard Analytics (2 minutes)

**Key message:** MongoDB aggregation framework powers real-time dashboards entirely server-side.

### Navigate to Dashboard

58. Show the 4 stat cards, pie chart, line chart, bar chart, and corridors table
59. Click **View Aggregation Pipeline** under the Daily Activity chart
    - Show the `$match` + `$group` + `$dateToString` pipeline
60. Click **View Aggregation Pipeline** under the Status Distribution chart
    - Show the `$group` + `$sort` pipeline

> **Say:** "Every chart on this dashboard is powered by a MongoDB aggregation pipeline. $facet runs all 4 in a single pass. In SQL, this would be 4 separate GROUP BY queries."

---

## Act 7: Value Propositions & Collections (2 minutes)

**Key message:** MongoDB replaces 4–5 systems with one platform.

### Value Propositions

61. Navigate to **Value Propositions**
62. Click through the highlights:
    - **Flexible Schema:** Side-by-side polymorphic documents with >>> markers on type-specific fields
    - **Indexing Strategies:** Show partial indexes — 85% smaller than full indexes for type-specific queries
    - **Vector Search:** Live embedding coverage, 2 index definitions, 3 use case pipelines
    - **Aggregation Framework:** The actual `$facet` pipeline powering the dashboard

### Collection Explorer

63. Navigate to **Collection Explorer**
64. Click the `payments` collection
    - Show: 16 regular indexes (compound, partial, unique, TTL, nested)
    - Show: 2 vector search indexes (payment + remittance)
    - Show: the JSON Schema validator enforcing UETR format, currency codes, status enums
65. Click the `agent_memory` collection
    - Show: polymorphic memory types in one collection with vector index

---

## Closing (30 seconds)

> *"Everything you saw — polymorphic payment storage, real-time event streaming, vector search, multi-agent memory, audit logging, data lifecycle management — all runs on one MongoDB cluster.*
>
> *No Kafka for events. No Elasticsearch for search. No Redis for caching. No pg_cron for TTL. No separate vector database.*
>
> *One database. One query language. One operational platform. That's MongoDB for Payments."*

---

## Quick Reference

### Terminal Commands

```bash
# Generate payments for Live Feed demo (1 per second)
python scripts/generate_payments.py --count 15 --delay 1

# Generate only payment returns (for return detection demo)
python scripts/generate_payments.py --count 5 --type pacs.004 --delay 2

# Generate all 5 types
python scripts/generate_payments.py --count 25

# Regenerate embeddings (after adding new payments)
python scripts/generate_embeddings.py
```

### Key URLs

| URL | Page | Demo Purpose |
|-----|------|-------------|
| `/` | Dashboard | Live counters, aggregation pipelines |
| `/live` | Live Feed | Change Streams real-time events |
| `/payments/new` | New Payment | Polymorphic type selection |
| `/payments` | All Payments | Unified list, type filter, MongoDB query |
| `/ai-search` | AI Search | Vector search (3 tabs) |
| `/agents` | AI Agents | Multi-agent, memory, metrics, feedback |
| `/value-props` | Value Propositions | 9 MongoDB capabilities with live data |
| `/collections` | Collection Explorer | Schemas, indexes, validators |

### MongoDB Features Demonstrated

| # | Feature | Where to Demo |
|---|---------|--------------|
| 1 | Polymorphic Pattern | New Payment → All Payments |
| 2 | Document Model (zero JOINs) | Payment Detail, Value Props |
| 3 | Change Streams | Live Feed, Dashboard counters, status tracking |
| 4 | Atlas Vector Search | AI Search (3 tabs) |
| 5 | Multi-Agent Memory | AI Agents → Memory Inspector |
| 6 | Aggregation Framework | Dashboard pipelines, Value Props |
| 7 | Schema Validation | Collection Explorer → payments |
| 8 | Atomic Operations | Status update ($set + $push) |
| 9 | Decimal128 | Value Props → precision comparison |
| 10 | TTL Indexes | Value Props → data lifecycle |
| 11 | Partial Indexes | Value Props → Indexing Strategies |
| 12 | Nested Field Indexes | Collection Explorer → index JSON |
| 13 | Memory Consolidation | AI Agents → Memory Consolidation tab |
| 14 | Tool Call Audit Trail | AI Agents → Tool Logs tab |
| 15 | User Feedback | AI Agents → thumbs up/down |
| 16 | Multi-Turn Conversations | AI Agents → follow-up questions |

### MongoDB vs Relational (Key Talking Points)

| Capability | MongoDB | Without MongoDB |
|-----------|---------|----------------|
| 5 payment types | 1 collection | 5+ tables with JOINs or NULLs |
| Complete payment read | 1 document | 8+ table JOINs |
| Real-time events | Change Streams | Kafka + Debezium |
| Semantic search | Atlas Vector Search | Elasticsearch or Pinecone |
| Data expiry | TTL indexes | pg_cron or app-level cron |
| Agent memory | 1 collection (vector + TTL + polymorphic) | 3+ tables + pgvector + pg_cron |
| Audit trail | Append-only with TTL | Separate logging system |
| Total infrastructure | 1 MongoDB cluster | 4–5 separate systems |
