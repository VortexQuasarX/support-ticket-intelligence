"""FastAPI Application Entrypoint with CORS and Startup Ingestion Lifespan."""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.database.db_manager import db_manager
from app.ingestion.pipeline import ingestion_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("support_tickets_app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure DB is initialized and CSV data is ingested
    logger.info("Initializing database and verifying data ingestion...")
    db_manager.init_database()
    count = db_manager.get_ticket_count()
    if count == 0:
        logger.info("Database is empty. Running initial CSV ingestion...")
        ingestion_pipeline.run()
    else:
        logger.info(f"Database ready with {count} support tickets.")
    yield
    # Shutdown
    logger.info("Application shutting down.")


app = FastAPI(
    title="Support Ticket Intelligence AI",
    description="Production-grade AI system for support ticket analytics, Text-to-SQL Q&A, and anomaly detection.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    from app.config import API_HOST, API_PORT
    uvicorn.run("app.main:app", host=API_HOST, port=API_PORT, reload=True)
