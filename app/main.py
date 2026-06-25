from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.router import api_router
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import admin_router
from app.api.websocket import router as websocket_router
from app.core.database import engine, Base
from app.models import *

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fitness App API")

@app.on_event("startup")
async def startup_event():
    import asyncio
    from app.services.scheduler import start_scheduler
    from app.services.notification_worker import start_notification_worker
    from app.services.notification_job_generator import start_daily_job_generator
    from app.services.push_retry_worker import start_push_retry_worker
    asyncio.create_task(start_scheduler())
    asyncio.create_task(start_notification_worker())
    asyncio.create_task(start_daily_job_generator())
    asyncio.create_task(start_push_retry_worker())

# Configure CORS for admin frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React Admin Dev
        
        # Add your production admin domain here
        "https://fitness-app-dashboard-eight.vercel.app"
        # "https://admin.yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Mount static files for media directory
app.mount("/media", StaticFiles(directory="app/media"), name="media")

# Include API routes
app.include_router(api_router, prefix="/api")
app.include_router(websocket_router, prefix="/ws")

@app.get("/")
def root():
    return {"message": "Fitness App API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
