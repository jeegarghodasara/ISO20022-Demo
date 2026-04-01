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
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   React + Vite  │────>│  FastAPI (Python)│────>│     MongoDB      │
│   Port 5173     │     │   Port 8000      │     │                  │
│                 │     │                  │     │   Polymorphic    │
│  - Dashboard    │     │  - REST API      │     │   payments       │
│  - New Payment  │     │  - Aggregations  │     │   collection     │
│    (type picker)│     │  - Schema Valid. │     │   stores all 5   │
│  - Payment List │     │  - Polymorphic   │     │   message types  │
│    (type filter)│     │    handlers      │     │                  │
│  - Statements   │     │                  │     │   12 collections │
│  - Investigations│    │                  │     │   total          │
└─────────────────┘     └─────────────────┘     └──────────────────┘
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
| **TTL Indexes** | Auto-expiry for notifications (90 days) and status reports (1 year) |
| **Compound Indexes** | Optimized queries by `messageType + status + date`, `IBAN + date`, `BIC + date` |
| **Flexible Indexing** | Sparse indexes on type-specific fields (`originalUetr`, `mandateId`) |

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

### Statements
- `GET /api/statements` -- List camt.053 statements
- `GET /api/statements/{id}` -- Statement header with all entries

### Investigations
- `GET /api/investigations` -- List cases
- `POST /api/investigations` -- Create investigation case
- `PUT /api/investigations/{caseId}/resolve` -- Resolve with atomic message append

### Analytics (Aggregation Framework)
- `GET /api/analytics/dashboard` -- Summary stats, status/currency distribution, daily activity
- `GET /api/analytics/top-corridors` -- Payment corridors by volume
- `GET /api/analytics/agent-activity` -- Multi-faceted agent analysis with `$facet`
- `GET /api/analytics/processing-times` -- Computed from embedded status history

### MongoDB Value Propositions
- `GET /api/value-props/summary` -- All 7 value propositions
- `GET /api/value-props/document-model` -- Document model vs relational comparison
- `GET /api/value-props/flexible-schema` -- Polymorphic message handling
- `GET /api/value-props/aggregation-power` -- Live `$facet` aggregation demo
- `GET /api/value-props/schema-validation` -- JSON Schema validator details
- `GET /api/value-props/atomic-operations` -- `$set` + `$push` vs SQL transactions
- `GET /api/value-props/decimal128-precision` -- Financial precision examples
- `GET /api/value-props/ttl-indexes` -- Data lifecycle management

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19, Vite 8, React Router 6, Recharts, Lucide Icons |
| **Backend** | Python 3.12, FastAPI, Motor (async MongoDB driver), Pydantic |
| **Database** | MongoDB 7.0+ with Decimal128, TTL indexes, JSON Schema validation |
| **Containerization** | Docker, Docker Compose |

## Project Structure

```
Payments-demo/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + lifespan
│   │   ├── config.py            # Pydantic settings (.env)
│   │   ├── database.py          # MongoDB connection, indexes, schema validation
│   │   ├── routes/
│   │   │   ├── payments.py      # Polymorphic payment CRUD
│   │   │   ├── initiations.py   # Batch payment initiations
│   │   │   ├── statements.py    # Bank statements
│   │   │   ├── investigations.py# Exception handling
│   │   │   ├── mandates.py      # Direct debit mandates
│   │   │   ├── analytics.py     # Aggregation pipelines
│   │   │   └── value_props.py   # MongoDB feature demos
│   │   └── utils/
│   │       └── helpers.py       # UETR generation, Decimal128 helpers
│   ├── scripts/
│   │   └── seed_data.py         # Database seeder (870 lines of realistic data)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Route definitions
│   │   ├── components/
│   │   │   ├── Layout.jsx       # Sidebar navigation
│   │   │   ├── StatusBadge.jsx  # Payment status badges
│   │   │   └── MessageTypeBadge.jsx  # Payment type badges
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx    # Analytics charts
│   │   │   ├── NewPayment.jsx   # Type picker + dynamic form
│   │   │   ├── Payments.jsx     # Payment list with type filter
│   │   │   ├── PaymentDetail.jsx# Type-specific detail view
│   │   │   ├── Statements.jsx   # Statement list
│   │   │   ├── StatementDetail.jsx
│   │   │   ├── Investigations.jsx
│   │   │   └── ValueProps.jsx   # MongoDB value proposition showcase
│   │   └── services/
│   │       └── api.js           # API client
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml
```

## License

This project is a demonstration application for educational purposes.
