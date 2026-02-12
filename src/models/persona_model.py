"""
Project Steak-Holder
Agent Persona model

details designed to be evident in responses
can be overridden by applying another persona
with DI at container launch

contains:
- persona
- project details
- conversation history
- placeholder for request message
"""

from pydantic import BaseModel, ConfigDict
from typing import List


class ExpertiseLevel(BaseModel):
    business: str
    technology: str
    model_config = ConfigDict(extra="allow")


class PersonalityFocus(BaseModel):
    can_tangent: bool
    refocus_easily: bool
    model_config = ConfigDict(extra="allow")


class Personality(BaseModel):
    tone: List[str]
    professionalism: str
    focus: PersonalityFocus
    model_config = ConfigDict(extra="allow")


class CommunicationRules(BaseModel):
    avoid: List[str]
    model_config = ConfigDict(extra="allow")


class Persona(BaseModel):
    name: str
    role: str
    location: str
    background: List[str]
    goals: List[str]
    expertise_level: ExpertiseLevel
    personality: Personality
    communication_rules: CommunicationRules
    model_config = ConfigDict(extra="allow")
