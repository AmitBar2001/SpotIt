from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.logger import logger
from app.routes import router
from app.security import get_api_key

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Demucs Audio Separator",
    description="An API to separate audio files into their instrumental stems (drums, bass, vocals, other) using the Demucs model. Can process direct file uploads or audio from YouTube links.",
    version="1.1.0",
)

# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router
app.include_router(router, dependencies=[Depends(get_api_key)])

# --- API Endpoints ---
@app.get(
    "/",
    summary="Root Endpoint",
    description="A simple root endpoint to check if the service is running.",
)
async def root():
    logger.info("Root endpoint called")
    return {"message": "Welcome to the Demucs Audio Separator API."}
