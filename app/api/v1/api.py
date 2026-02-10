from fastapi import APIRouter

from . import analysis, auth, cognitive, evaluation, scan, shift, firebase, detection, check, admin

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(shift.router)
api_router.include_router(scan.router)
api_router.include_router(analysis.router)
api_router.include_router(cognitive.router)
api_router.include_router(evaluation.router)
api_router.include_router(firebase.router)
api_router.include_router(detection.router)
api_router.include_router(check.router)
api_router.include_router(admin.router)
