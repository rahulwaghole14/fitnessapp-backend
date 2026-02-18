from fastapi import APIRouter
from .v1.router import router as v1_router
from .admin.router import admin_router as admin_router

api_router = APIRouter()


api_router.include_router(v1_router, prefix="/v1", tags=["v1"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
