"""
Project Steak-Holder
model definition for context model
intended to package all relevant information

contains:
- persona
- project details
- conversation history
- placeholder for request message
"""

from pydantic import BaseModel
from typing import Optional, List

from src.models.persona_model import Persona
from src.models.project_model import Project
from src.models.message_model import Message


class LlmQuery(BaseModel):
    request: Optional[str]
    history: Optional[List[Message]] = None  # <-remove "None" once persistence implemented
    persona: Optional[Persona]
    project: Optional[Project]