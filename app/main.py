from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.router import api_router
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import admin_router
from app.core.database import engine, Base
from app.models import *

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fitness App API")

# Configure CORS for admin frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React Admin Dev
        # Add your production admin domain here
        # "https://admin.yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Mount static files for media directory
app.mount("/media", StaticFiles(directory="app/media"), name="media")

# Include API routes
app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Fitness App API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
