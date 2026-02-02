from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.router import api_router
from app.core.database import engine, Base
from app.models import *

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fitness App API")

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
