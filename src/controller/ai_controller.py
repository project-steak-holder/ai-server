"""
AIController is responsible for:
                                handling incoming agent query requests from front end with FastAPI
                                validating JWT tokens using Neon (auth service injected into FastAPI)
                                delegating processing to AgentService
"""

from fastapi import HTTPException
from src.service.agent_service import AgentService


class AIController:
    """FastAPI Controller for handling incoming requests from the front end
        only a single route is needed for MVP
        Neon Auth injected for authentication of JWT in request header
    """
