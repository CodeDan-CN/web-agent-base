from fastapi import APIRouter

from web.ag_ui import ag_ui_router
from web.agent import agent_router, session_router
from web.health import health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(agent_router)
api_router.include_router(ag_ui_router)
api_router.include_router(session_router)
