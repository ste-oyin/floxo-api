from fastapi import APIRouter

from app.api.v1.endpoints import analytics, auth, floor_plans, jobs, videos
from app.api.v1.endpoints.admin import jobs as admin_jobs
from app.api.v1.endpoints.admin import system as admin_system
from app.api.v1.endpoints.admin import users as admin_users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(floor_plans.router, prefix="/floor-plans", tags=["floor-plans"])
api_router.include_router(videos.router, prefix="/videos", tags=["videos"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(analytics.suggestions_router, tags=["suggestions"])
api_router.include_router(admin_users.router, prefix="/admin/users", tags=["admin-users"])
api_router.include_router(admin_jobs.router, prefix="/admin/jobs", tags=["admin-jobs"])
api_router.include_router(admin_system.router, prefix="/admin/system", tags=["admin-system"])
