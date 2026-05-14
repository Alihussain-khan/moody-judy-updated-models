from fastapi import APIRouter
from app.api.V1.endpoints.jobs import router as jobs_router
from app.api.V1.endpoints.events import router as events_router

router = APIRouter()
router.include_router(jobs_router)
router.include_router(events_router)