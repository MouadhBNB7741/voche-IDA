import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.postgres import PostgresDB
from app.db.redis import connect_redis, disconnect_redis
from app.db.init_db import init_db
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.clinical import router as clinical_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("🚀 VOCE Backend Starting up...")
    try:
        await PostgresDB.connect()
        logger.info("Database connected.")
        await init_db()
    except Exception as e:
        logger.exception("Database connection or initialization failed")
    try:
        await connect_redis()
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        
    yield
    # --- Shutdown ---
    logger.info("🛑 VOCE Backend Shutting down...")
    await PostgresDB.disconnect()
    await disconnect_redis()

app = FastAPI(
    title=settings.project_name,
    description="VOCE Platform API for Clinical Trials & Community",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json"
)

os.makedirs("uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="uploads"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(clinical_router, prefix="/api/v1")


@app.get("/api/v1/", tags=["Status"])
async def root():
    return {
        "message": "VOCE Backend API is running",
        "docs_url": "/api/v1/docs", 
        "redoc_url": "/redoc"
    }

@app.get("/api/v1/health", tags=["Status"])
async def health_check():
    return {
        "status": "online",
        "database": "connected",
        "redis": "connected",
        "version": "0.1.0"
    }