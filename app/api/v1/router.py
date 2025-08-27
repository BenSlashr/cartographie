from fastapi import APIRouter
from app.api.v1.endpoints import projects

api_router = APIRouter()
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])

# Note: jobs endpoint removed - using simple async analysis instead