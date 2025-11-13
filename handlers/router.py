from aiogram import Router
import logging
from .start import router as start_router
from .goals import router as goals_router
from .smart import router as smart_router
from .ai import router as ai_router
from .progress import router as progress_router
from .navigation import router as navigation_router
from .analysis import router as analysis_router


logging.basicConfig(level=logging.INFO)

main_router = Router()
main_router.include_router(start_router)
main_router.include_router(goals_router)
main_router.include_router(smart_router)
main_router.include_router(ai_router)
main_router.include_router(progress_router)
main_router.include_router(navigation_router)
main_router.include_router(analysis_router)
