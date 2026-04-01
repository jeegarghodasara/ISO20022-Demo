from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import connect_to_mongo, close_mongo_connection
from app.routes import (
    payments,
    statements,
    investigations,
    analytics,
    initiations,
    mandates,
    value_props,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(
    title="ISO 20022 Global Payment System",
    description="A MongoDB-powered global payment processing system implementing ISO 20022 standards",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(
    initiations.router, prefix="/api/initiations", tags=["Payment Initiations"]
)
app.include_router(statements.router, prefix="/api/statements", tags=["Statements"])
app.include_router(
    investigations.router, prefix="/api/investigations", tags=["Investigations"]
)
app.include_router(mandates.router, prefix="/api/mandates", tags=["Mandates"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(
    value_props.router, prefix="/api/value-props", tags=["MongoDB Value Props"]
)


@app.get("/api/health")
async def health_check():
    from app.database import get_database

    db = get_database()
    try:
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return {"status": "unhealthy", "database": "disconnected"}
