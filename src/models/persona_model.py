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

from pydantic import BaseModel
from typing import List


class ExpertiseLevel(BaseModel):
    business: str
    technology: str

    class Config:
        extra = "allow"


class PersonalityFocus(BaseModel):
    can_tangent: bool
    refocus_easily: bool

    class Config:
        extra = "allow"


class Personality(BaseModel):
    tone: List[str]
    professionalism: str
    focus: PersonalityFocus

    class Config:
        extra = "allow"


class CommunicationRules(BaseModel):
    avoid: List[str]

    class Config:
        extra = "allow"


class Persona(BaseModel):
    name: str
    role: str
    location: str
    background: List[str]
    goals: List[str]
    expertise_level: ExpertiseLevel
    personality: Personality
    communication_rules: CommunicationRules

    class Config:
        extra = "allow"
