from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routes import router as api_router
from sfa.api.routes import router as sfa_router
import logging
import os
from app.middlewares.logging_middleware import log_requests  # We'll move the middleware

app = FastAPI()


# CORS configuration
origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:3000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Add logging middleware
app.middleware("http")(log_requests)

# Create uploads directory if it doesn't exist
uploads_dir = "uploads"
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)
    print(f"Created uploads directory: {uploads_dir}")

# Mount static files for uploads folder
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

#  Include all API routes
app.include_router(
    api_router,
    prefix="/hrms"  # This will prefix all routes with /api
)
app.include_router(
    sfa_router,
    prefix="/sfa"  # This will prefix all routes with /api
)