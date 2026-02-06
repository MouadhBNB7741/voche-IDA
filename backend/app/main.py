import os
from fastapi.staticfiles import StaticFiles
import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.postgres import PostgresDB
from app.db.redis import connect_redis, disconnect_redis
from app.api.v1.auth import router as auth_router


async def startup():
    await PostgresDB.connect()
    await connect_redis()


async def shutdown():
    await PostgresDB.disconnect()
    await disconnect_redis()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await startup()
    yield
    # Shutdown
    await shutdown()


app = FastAPI(title=settings.project_name, lifespan=lifespan)

# Mount Static Files (Uploads)
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "SMS Gateway Server is running"}


@app.get("/health")
async def health_check():
    return {"status": "online"}
