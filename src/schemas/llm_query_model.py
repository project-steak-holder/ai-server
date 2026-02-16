"""
Project Steak-Holder
model definition for context model
intended to package all relevant information
"""

from pydantic import BaseModel, Field
from typing import Optional, List

from .persona_model import Persona
from .project_model import Project
from .message_model import Message


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
