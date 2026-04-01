# ISO 20022 Global Payment System Demo

A 3-tier application demonstrating a global payment processing system built on the **ISO 20022** standard with **MongoDB** as the database layer.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React + Vite  │────▶│  FastAPI (Python)│────▶│    MongoDB      │
│   Port 5173     │     │   Port 8000      │     │   Port 27017    │
│                 │     │                  │     │                 │
│  - Dashboard    │     │  - REST API      │     │  12 Collections │
│  - Payments     │     │  - Aggregations  │     │  - payments     │
│  - Statements   │     │  - Schema Valid. │     │  - statements   │
│  - Investigations│    │  - Value Props   │     │  - investigations│
│  - Value Props  │     │                  │     │  - mandates     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## MongoDB Value Propositions Highlighted

| Value Proposition | Where Demonstrated |
|---|---|
| **Document Model** | Single payment document contains parties, agents, charges, status history - no JOINs |
| **Flexible Schema** | 775+ ISO 20022 message types in polymorphic collections without schema migrations |
| **Aggregation Framework** | Dashboard analytics, top corridors, agent activity computed server-side with `$facet` |
| **Schema Validation** | UETR (UUID v4), currency (ISO 4217), status codes enforced at database level |
| **Atomic Operations** | Status update + history append in single `$set` + `$push` operation |
| **Decimal128** | Financial-grade precision for all monetary amounts |
| **TTL Indexes** | Auto-expiry: notifications (90 days), status reports (1 year) |
| **Compound Indexes** | Optimized for payment search by status + date, IBAN + date, BIC + date |

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- MongoDB 7.0+ (local or Atlas)

### Option 1: Local Development

**1. Start MongoDB** (if not already running):
```bash
mongod --dbpath /tmp/mongodb-data
```

**2. Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Seed the database with demo data
python scripts/seed_data.py

# Start the API server
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

## ISO 20022 Collections

| Collection | Messages | Purpose |
|---|---|---|
| `payments` | pacs.008, pacs.009, pacs.004 | Core payment transactions |
| `payment_initiations` | pain.001, pain.008 | Customer payment requests |
| `status_reports` | pacs.002 | FI-to-FI status reports |
| `statements` | camt.053 | End-of-day bank statements |
| `statement_entries` | camt.053 (entries) | Booked transaction entries |
| `notifications` | camt.054 | Real-time debit/credit notifications |
| `remittance_details` | remt.001 | Unbounded structured remittance |
| `investigations` | camt.026-056 | Exception handling cases |
| `mandates` | pain.009-012 | Direct debit mandates |
| `accounts` | acmt.007 | Account master data |
| `participants` | Reference | Financial institution registry |
| `original_messages` | All | Raw XML audit archive |

## API Endpoints

### Payments
- `GET /api/payments` - List with filters (status, currency, date, IBAN, BIC)
- `GET /api/payments/search?q=` - Multi-field search
- `GET /api/payments/{uetr}` - Full payment detail with remittance and status reports
- `POST /api/payments` - Create new pacs.008
- `PUT /api/payments/{uetr}/status` - Atomic status update
- `GET /api/payments/{uetr}/trace` - Payment trace with hop timeline

### Statements
- `GET /api/statements` - List camt.053 statements
- `GET /api/statements/{id}` - Statement with all entries

### Investigations
- `GET /api/investigations` - List cases
- `POST /api/investigations` - Create case
- `PUT /api/investigations/{caseId}/resolve` - Resolve with atomic message append

### Analytics (MongoDB Aggregation Framework)
- `GET /api/analytics/dashboard` - Summary stats, status/currency distribution, daily activity
- `GET /api/analytics/top-corridors` - Payment corridors by volume
- `GET /api/analytics/agent-activity` - `$facet` multi-aggregation
- `GET /api/analytics/processing-times` - Computed from embedded status history

### MongoDB Value Props
- `GET /api/value-props/summary` - All 7 value propositions
- `GET /api/value-props/document-model` - Document model vs relational comparison
- `GET /api/value-props/flexible-schema` - Polymorphic message handling
- `GET /api/value-props/aggregation-power` - Live `$facet` aggregation
- `GET /api/value-props/schema-validation` - JSON Schema validator details
- `GET /api/value-props/atomic-operations` - `$set` + `$push` vs SQL transactions
- `GET /api/value-props/decimal128-precision` - Financial precision
- `GET /api/value-props/ttl-indexes` - Data lifecycle management

## Tech Stack

- **Frontend:** React 19, Vite, React Router, Recharts, Lucide Icons
- **Backend:** Python 3.12, FastAPI, Motor (async MongoDB driver), Pydantic
- **Database:** MongoDB 7.0 with Decimal128, TTL indexes, schema validation
