"""
Project Steak-Holder
model definition for context model
intended to package all relevant information
"""

from pydantic import BaseModel, Field
from typing import Optional, List

from src.models.persona_model import Persona
from src.models.project_model import Project
from src.models.message_model import Message


class LlmQuery(BaseModel):
    """model contains:
                    - persona
                    - project details
                    - conversation history
                    - placeholder for request message
    """
    request: Optional[str]
    history: List[Message] = Field(default_factory=list)
    persona: Optional[Persona]
    project: Optional[Project]