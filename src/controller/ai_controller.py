"""
AIController is responsible for:
                                handling incoming agent query requests from FastAPI router
                                validating JWT tokens using Neon
                                delegating processing to AgentService
"""

from fastapi import HTTPException
from src.service.agent_service import AgentService
import os

class AIController:
    def __init__(self):
        self.agent_service = AgentService()


    # main entry point
    def handle_agent_query(self, req_payload: dict, headers: dict) -> dict:
        # extract token from header
        token = self._extract_jwt_token(headers)
        # validate
        if not self._validate_jwt_w_neon(token):
            raise HTTPException(status_code=401, detail="Unauthorized")
        # delegate to service layer
        return self.agent_service.process_agent_query(req_payload)


    # helper method to extract JWT from header
    def _extract_jwt_token(self, headers: dict) -> str:
        auth_header = headers.get("Authorization")
        # validate format
        if not auth_header or not auth_header.startswith("Bearer "):
            return ""
        # return extracted token
        return auth_header.split(" ", 1)[1]


    # helper method to validate JWT with Neon
    def _validate_jwt_w_neon(self, token: str) -> bool:
        pass
