from fastapi import APIRouter

from api.routers.upload import router as upload_router
from api.routers.classification import router as class_router
from api.routers.extraction import router as extract_router
from api.routers.data_review import router as review_router
from api.routers.boq import router as boq_router

router = APIRouter()

router.include_router(upload_router)
router.include_router(class_router)
router.include_router(extract_router)
router.include_router(review_router)
router.include_router(boq_router)
