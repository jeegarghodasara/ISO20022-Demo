# ISO 20022 Payment System Demo

A full-stack demo application showcasing how **MongoDB's flexible document model** handles the **polymorphic data structures** of the ISO 20022 financial messaging standard. Users can create, view, and manage five different payment types -- all stored in a single collection with type-specific fields -- demonstrating why MongoDB is a natural fit for payment processing systems.

## Why MongoDB for ISO 20022?

ISO 20022 defines 775+ message types with deeply nested XML structures. Each payment type (credit transfer, direct debit, payment return, etc.) shares common fields but also carries type-specific data. In a relational database, this requires either:

- **Table-per-type**: Dozens of tables with complex JOINs
- **Single table with sparse columns**: Hundreds of nullable columns, most empty
- **EAV pattern**: Unmaintainable key-value sprawl

MongoDB solves this with the **polymorphic pattern** -- all payment types coexist in one collection, each document containing exactly the fields it needs. No migrations when a new message type is added. No JOINs to assemble a complete payment. No wasted storage on NULL columns.

```
// pacs.008 - Customer Credit Transfer        // pacs.004 - Payment Return
{                                              {
  "messageType": "pacs.008",                     "messageType": "pacs.004",
  "uetr": "...",                                 "uetr": "...",
  "settlementAmount": Decimal128("50000"),        "settlementAmount": Decimal128("50000"),
  "debtor": { ... },                             "debtor": { ... },
  "creditor": { ... },                           "creditor": { ... },
  // Credit transfer specific                    // Return specific
  "exchangeRate": Decimal128("1.08"),             "originalUetr": "...",
  "chargeBearer": "SHAR",                        "returnReason": {
  "serviceLevel": "SEPA"                           "code": "AC04",
}                                                   "description": "Account closed"
                                                   }
                                                 }
```

## Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│   React + Vite   │────>│  FastAPI (Python) │────>│      MongoDB      │
│   Port 5173      │     │   Port 8000       │     │                   │
│                  │     │                   │     │  Polymorphic      │
│  - Dashboard     │ WS  │  - REST API       │     │  payments (5 types│
│  - Live Feed  <──┼─────┼── Change Streams  │<────┤  in one collection│
│  - AI Search     │     │  - Vector Search  │     │                   │
│  - AI Agents     │     │  - 5 AI Agents    │     │  Vector Search    │
│  - Payments      │     │  - WebSocket      │     │  indexes (3)      │
│  - Collections   │     │  - Aggregations   │     │                   │
│  - Value Props   │     │                   │     │  Agent memory     │
└──────────────────┘     └────────┬──────────┘     │  (3 types + TTL)  │
                                  │                │                   │
                         ┌────────▼──────────┐     │  15+ collections  │
                         │  Atlas AI Endpoint │     └───────────────────┘
                         │  voyage-finance-2  │
                         │  (1024 dim embeds) │
                         └───────────────────┘
```

## Supported Payment Types

| Type | ISO Message | Description | Type-Specific Fields |
|------|-------------|-------------|----------------------|
| **Customer Credit Transfer** | pacs.008 | Send money between customers via banks | `exchangeRate`, `chargeBearer`, `serviceLevel`, `instructedAmount` |
| **Bank-to-Bank Transfer** | pacs.009 | Direct transfer between financial institutions | `instructingAgent`, `instructedAgent`, `intermediaryAgent1` |
| **Payment Return** | pacs.004 | Return a previously received payment | `originalUetr`, `returnReason.code`, `originalPaymentRef` |
| **Payment Initiation** | pain.001 | Customer instructs bank to make payments | `initiatingParty`, `numberOfTransactions`, `controlSum`, `requestedExecutionDate` |
| **Direct Debit Initiation** | pain.008 | Creditor collects funds from debtor | `mandateId`, `creditorSchemeId`, `sequenceType`, `requestedCollectionDate` |

All five types share common fields (`uetr`, `settlementAmount`, `settlementCurrency`, `status`, `debtor`, `creditor`, `statusHistory`) and are stored in a single `payments` collection.

## MongoDB Features Demonstrated

| Feature | How It's Used |
|---------|---------------|
| **Polymorphic Pattern** | 5 payment types in one collection with type-specific fields |
| **Document Model** | Complete payment with parties, agents, charges, status history in a single document |
| **Schema Validation** | JSON Schema enforces required fields, UETR format (UUID v4), currency codes (ISO 4217), status enums -- while allowing type-specific fields to vary |
| **Atomic Operations** | Status update + history append via `$set` + `$push` in one operation |
| **Aggregation Framework** | Dashboard analytics, payment type distribution, top corridors with `$facet` |
| **Decimal128** | Financial-grade precision for all monetary amounts |
| **TTL Indexes** | Auto-expiry for notifications (90 days), status reports (1 year), agent messages (24hrs), episodic memory (90 days) |
| **Compound Indexes** | Optimized queries by `messageType + status + date`, `IBAN + date`, `BIC + date` |
| **Flexible Indexing** | Sparse indexes on type-specific fields (`originalUetr`, `mandateId`) |
| **Atlas Vector Search** | Natural language payment search, similar transaction detection, smart remittance matching, agent memory recall |
| **Change Streams** | Live Feed page, real-time dashboard counters, payment status tracking, automated return detection |
| **WebSocket** | Real-time event streaming from Change Streams to browser clients |
| **Multi-Agent Architecture** | 5 AI agents with MongoDB-backed memory (episodic/semantic/procedural) |

## MongoDB vs Postgres -- Why MongoDB Excels for Payments

### 1. Polymorphic Payment Types

**MongoDB**: 5 payment types in one `payments` collection. Each document stores only the fields it needs. Adding a 6th type requires zero schema changes.

**Postgres**: Three bad options:
- Single table with 40+ nullable columns, most NULL per row
- Table-per-type with JOINs to a shared `payments` table and `UNION ALL` across types
- EAV pattern that destroys type safety and query performance

### 2. Nested Document Model (Zero JOINs)

**MongoDB**: A single payment document contains debtor, creditor, agents, charges, status history, remittance -- all embedded. One read returns everything.

**Postgres**: The same read requires JOINs across `payments`, `parties`, `party_addresses`, `party_accounts`, `agents`, `charges`, `status_log`, `remittance` -- at least 8 tables, 15+ lines of SQL.

### 3. Vector Search (No External Infrastructure)

**MongoDB**: Atlas Vector Search indexes sit on the same cluster. `$vectorSearch` runs in a standard aggregation pipeline alongside `$match`, `$project`, `$sort`. Pre-filter by `messageType` or `status` BEFORE computing vector similarity.

**Postgres**: pgvector exists but has no pre-filtering in the vector index, no managed service, and can't combine vector search with aggregation pipelines. Most teams add Elasticsearch or Pinecone alongside Postgres for production.

### 4. Change Streams (Built-in Event Sourcing)

**MongoDB**: `db.payments.watch()` streams real-time events with guaranteed ordering and resume tokens. Live Feed, real-time dashboard counters, status tracking, and return detection all run off one Change Stream.

**Postgres**: `LISTEN/NOTIFY` has no persistence, no resume, 8KB payload limit. Logical replication requires WAL configuration. Most teams add Kafka or Debezium as middleware.

### 5. Agent Memory (Polymorphic + Vector + TTL Combined)

**MongoDB**: One `agent_memory` collection stores 3 memory types with vector embeddings for recall, TTL for decay, and aggregation for knowledge building.

**Postgres**: Requires 3+ tables + pgvector extension + pg_cron for TTL + application-level logic to combine vector similarity with recency/frequency scoring.

### 6. Summary

| Capability | MongoDB | Postgres |
|-----------|---------|----------|
| Polymorphic types | Native -- one collection | ALTER TABLE / NULLs / table-per-type |
| Nested documents | Embedded, zero JOINs | 8+ table JOINs |
| Vector search | Atlas Vector Search, same cluster | pgvector, no pre-filtering in index |
| Change streams | Built-in, resume tokens | LISTEN/NOTIFY (limited) or Kafka |
| TTL expiry | Index-level, automatic | pg_cron or app-level cron |
| Schema flexibility | Validate common, allow type-specific | All-or-nothing DDL |
| Financial precision | Decimal128 native | NUMERIC (equally strong) |
| Agent memory | One collection: vector + TTL + polymorphic | 3+ tables + pgvector + pg_cron |
| Aggregation | `$facet` for parallel pipelines | Multiple queries or CTEs |
| Infrastructure | One cluster for everything | Postgres + Kafka + Elasticsearch + cron |

**The core argument: MongoDB replaces 4-5 systems** (relational DB + message queue + search engine + cron scheduler + vector DB) **with one platform.** This demo proves it.

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- MongoDB 7.0+ (local or [Atlas](https://www.mongodb.com/atlas))

### Option 1: Local Development

**1. Start MongoDB** (skip if using Atlas):
```bash
mongod --dbpath /tmp/mongodb-data
```

**2. Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `backend/.env` file:
```env
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=iso20022_payments
HOST=0.0.0.0
PORT=8000
```

Seed the database and start the server:
```bash
python scripts/seed_data.py
uvicorn app.main:app --reload --port 8000
```

**3. Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**4. Open** http://localhost:5173

### Option 2: Docker Compose

```bash
docker compose up -d

# Seed data (after services are up)
docker compose exec backend python scripts/seed_data.py
```

Open http://localhost:5173

## Using the Demo

### Creating a Payment

1. Click **New Payment** in the sidebar
2. Select one of the 5 payment types from the card picker
3. Fill in the type-specific form (fields change based on the selected type)
4. Review the live **Document Schema Preview** showing the polymorphic structure
5. Submit -- the document is inserted atomically into MongoDB

### Viewing Payments

- The **All Payments** page shows every payment type in a unified list
- Filter by **Payment Type** to see only credit transfers, returns, etc.
- Filter by **Status** or **Currency**
- Click any payment to see its detail view with type-specific sections:
  - Return Details (pacs.004): original UETR link, reason code
  - Initiation Details (pain.001): initiating party, transaction count
  - Direct Debit Details (pain.008): mandate ID, sequence type
  - Agent Chain (pacs.009): instructing/instructed/intermediary agents

### Updating Status

On the payment detail page, click **Set ACSP**, **Set ACSC**, or **Set RJCT** to update the status. This demonstrates MongoDB's atomic `$set` + `$push` -- the status field and the status history array are updated in a single operation with no race conditions.

### Live Feed (Change Streams)

1. Open the **Live Feed** page in the sidebar
2. In a terminal, run: `python scripts/generate_payments.py --count 20 --delay 1`
3. Watch payments slide in one per second with type badges and amounts
4. The **Dashboard** counters also update in real-time via the same Change Stream

### AI Search (Vector Search)

1. Go to **AI Search** in the sidebar
2. Try **Natural Language**: "large transfers to Germany that were rejected"
3. Try **Remittance Matching**: "Invoice 3974 from ACME"
4. Try **Similar Transactions**: paste a UETR to find structurally similar payments
5. Each search shows the `$vectorSearch` aggregation pipeline used

### AI Agents (Multi-Agent Architecture)

1. Go to **AI Agents** in the sidebar
2. Paste a payment UETR and ask: "Run a full analysis with all agents"
3. The Orchestrator delegates to 4 specialist agents (Routing, Compliance, Exception, Reconciliation)
4. Each agent recalls relevant memories from past decisions via Vector Search
5. Click an agent card and **View Memory Inspector** to see episodic memories accumulate
6. Ask more questions -- agents get smarter as they build memory

### Collection Explorer

Go to **Collection Explorer** under MongoDB to browse all collections, view document schemas, regular indexes (as JSON), vector search indexes, and schema validators.

## ISO 20022 Collections

| Collection | Messages | Purpose |
|------------|----------|---------|
| `payments` | pacs.008, pacs.009, pacs.004, pain.001, pain.008 | **Polymorphic** -- all payment types in one collection |
| `payment_initiations` | pain.001 | Batch payment initiation records |
| `status_reports` | pacs.002 | FI-to-FI status reports (TTL: 1 year) |
| `statements` | camt.053 | End-of-day bank statements |
| `statement_entries` | camt.053 (entries) | Booked transaction entries |
| `notifications` | camt.054 | Real-time debit/credit notifications (TTL: 90 days) |
| `remittance_details` | remt.001 | Unbounded structured remittance (separate collection to prevent document growth) |
| `investigations` | camt.026-056 | Exception handling and cancellation cases |
| `mandates` | pain.009-012 | Direct debit mandate lifecycle |
| `accounts` | acmt.007 | Account master data |
| `participants` | Reference | Financial institution registry |
| `original_messages` | All | Raw message audit archive |

## API Endpoints

### Payments (Polymorphic)
- `GET /api/payments` -- List with filters (`status`, `currency`, `message_type`, `date_from`, `date_to`, `debtor_iban`, `creditor_iban`)
- `GET /api/payments/search?q=` -- Multi-field search across all payment types
- `GET /api/payments/types` -- Payment type distribution (aggregation)
- `GET /api/payments/{uetr}` -- Full detail with type-specific fields, remittance, and status reports
- `POST /api/payments` -- Create any payment type (polymorphic handler)
- `PUT /api/payments/{uetr}/status` -- Atomic status update with history append
- `GET /api/payments/{uetr}/trace` -- Payment trace with hop timeline

### AI Vector Search
- `GET /api/ai-search/status` -- Embedding coverage and index status
- `POST /api/ai-search/natural-language` -- Natural language payment search
- `POST /api/ai-search/similar-transactions` -- Find similar payments by UETR
- `POST /api/ai-search/remittance-match` -- Semantic remittance/invoice matching

### AI Agents (Multi-Agent Architecture)
- `GET /api/agents` -- List all agents with memory/message counts
- `POST /api/agents/ask` -- Ask an agent or orchestrator to analyze a payment
- `GET /api/agents/memory/{agentId}` -- Browse an agent's memories
- `GET /api/agents/memory-stats` -- Memory statistics across all agents
- `GET /api/agents/messages` -- Recent inter-agent messages
- `GET /api/agents/conversations` -- Recent agent conversations

### WebSocket (Change Streams)
- `WS /ws/payments` -- Real-time payment events (insert, update, return detection)

### Statements
- `GET /api/statements` -- List camt.053 statements
- `GET /api/statements/{id}` -- Statement header with all entries

### Investigations
- `GET /api/investigations` -- List cases
- `POST /api/investigations` -- Create investigation case
- `PUT /api/investigations/{caseId}/resolve` -- Resolve with atomic message append

### Analytics (Aggregation Framework)
- `GET /api/analytics/dashboard` -- Summary stats, status/currency distribution, daily activity (with pipeline JSON)
- `GET /api/analytics/top-corridors` -- Payment corridors by volume
- `GET /api/analytics/agent-activity` -- Multi-faceted agent analysis with `$facet`
- `GET /api/analytics/processing-times` -- Computed from embedded status history

### Collection Explorer
- `GET /api/collections` -- List all collections with doc counts
- `GET /api/collections/{name}` -- Schema shape, sample document, regular indexes, vector indexes, validator

### MongoDB Value Propositions
- `GET /api/value-props/summary` -- All 8 value propositions
- `GET /api/value-props/document-model` -- Document model vs relational comparison
- `GET /api/value-props/flexible-schema` -- Polymorphic message handling with live samples
- `GET /api/value-props/aggregation-power` -- Live `$facet` aggregation with pipeline JSON
- `GET /api/value-props/schema-validation` -- JSON Schema validator details
- `GET /api/value-props/atomic-operations` -- `$set` + `$push` vs SQL transactions
- `GET /api/value-props/decimal128-precision` -- Financial precision examples
- `GET /api/value-props/ttl-indexes` -- Data lifecycle management
- `GET /api/value-props/vector-search` -- Vector search use cases and index definitions

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19, Vite 8, React Router 6, Recharts, Lucide Icons |
| **Backend** | Python 3.12, FastAPI, Motor (async MongoDB driver), Pydantic |
| **Database** | MongoDB 7.0+ with Decimal128, TTL indexes, JSON Schema validation |
| **AI/Embeddings** | Voyage Finance 2 via MongoDB Atlas AI endpoint (1024 dimensions) |
| **Real-time** | MongoDB Change Streams + FastAPI WebSocket |
| **Design** | MongoDB LeafyGreen design system (dark mode) |
| **Containerization** | Docker, Docker Compose |

## Project Structure

```
Payments-demo/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + lifespan + Change Stream watcher
│   │   ├── config.py            # Pydantic settings (.env)
│   │   ├── database.py          # MongoDB connection, indexes, schema validation
│   │   ├── agents/
│   │   │   ├── memory.py        # Agent memory service (episodic/semantic/procedural)
│   │   │   ├── message_bus.py   # Inter-agent communication via MongoDB
│   │   │   └── specialists.py   # 5 specialized agents (routing, compliance, etc.)
│   │   ├── routes/
│   │   │   ├── payments.py      # Polymorphic payment CRUD
│   │   │   ├── ai_search.py     # Vector search (natural language, similar, remittance)
│   │   │   ├── agents.py        # Multi-agent orchestration API
│   │   │   ├── websocket.py     # Change Stream → WebSocket bridge
│   │   │   ├── collections.py   # Collection explorer (schema, indexes)
│   │   │   ├── analytics.py     # Aggregation pipelines (with pipeline JSON)
│   │   │   ├── value_props.py   # MongoDB value proposition demos
│   │   │   ├── initiations.py   # Batch payment initiations
│   │   │   ├── statements.py    # Bank statements
│   │   │   ├── investigations.py# Exception handling
│   │   │   └── mandates.py      # Direct debit mandates
│   │   └── utils/
│   │       ├── helpers.py       # UETR generation, Decimal128 helpers
│   │       └── embeddings.py    # Voyage AI via Atlas AI endpoint
│   ├── scripts/
│   │   ├── seed_data.py         # Database seeder (870 lines of realistic data)
│   │   ├── generate_payments.py # Standalone payment generator via REST API
│   │   └── generate_embeddings.py # Batch embedding generator for vector search
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Route definitions + context providers
│   │   ├── components/
│   │   │   ├── Layout.jsx       # Fixed header + sidebar navigation
│   │   │   ├── StatusBadge.jsx  # Payment status badges
│   │   │   └── MessageTypeBadge.jsx  # Payment type badges
│   │   ├── context/
│   │   │   ├── AgentContext.jsx  # Persistent agent state across navigation
│   │   │   └── AISearchContext.jsx # Persistent search state across navigation
│   │   ├── hooks/
│   │   │   └── usePaymentStream.js # WebSocket hook for Change Stream events
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx    # Analytics charts + live counters
│   │   │   ├── LiveFeed.jsx     # Real-time Change Stream event feed
│   │   │   ├── NewPayment.jsx   # Type picker + dynamic form
│   │   │   ├── Payments.jsx     # Payment list + MongoDB query preview
│   │   │   ├── PaymentDetail.jsx# Type-specific detail + live status tracking
│   │   │   ├── AISearch.jsx     # Vector search (3 tabs) + pipeline preview
│   │   │   ├── Agents.jsx       # Multi-agent dashboard + Ask + Memory Inspector
│   │   │   ├── Collections.jsx  # Collection explorer (schema, indexes)
│   │   │   ├── ValueProps.jsx   # 8 MongoDB value propositions
│   │   │   ├── Statements.jsx   # Statement list
│   │   │   ├── StatementDetail.jsx
│   │   │   └── Investigations.jsx
│   │   └── services/
│   │       └── api.js           # API client
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml
```

## License

This project is a demonstration application for educational purposes.
