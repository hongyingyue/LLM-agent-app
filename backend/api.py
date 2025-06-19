from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from loguru import logger
import os
from backend.routers import auth, session, message, file, tool
from backend.database import init_db


log_path = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_path, exist_ok=True)
logger.add(
    os.path.join(log_path, "api.log"),
    rotation="50 MB",  # Rotate when file reaches 50MB
    retention="7 days",  # Keep logs for 7 days
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    encoding="utf-8"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
    expose_headers=["*"],
    max_age=3600,
)

# Mount static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

app.include_router(auth.router, prefix="/api/auth")
app.include_router(session.router, prefix="/api/sessions")
app.include_router(message.router, prefix="/api/messages", tags=["messages"])
app.include_router(file.router, prefix="/api/files")


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Start server on 0.0.0.0:8000")
    uvicorn.run(
        "backend.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
