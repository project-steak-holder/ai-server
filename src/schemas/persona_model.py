"""
Project Steak-Holder
Agent Persona model

details designed to be evident in responses
can be overridden by applying another persona
with DI at container launch
"""

from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class ExpertiseLevel(BaseModel):
    """component of Persona model"""

    business: str
    technology: str
    model_config = ConfigDict(extra="allow", frozen=True)


class PersonalityFocus(BaseModel):
    """component of Personality model"""

    can_tangent: bool
    refocus_easily: bool
    model_config = ConfigDict(extra="allow", frozen=True)


class Personality(BaseModel):
    """component of Persona model"""

    tone: List[str]
    professionalism: str
    focus: PersonalityFocus
    sentiment: float = 0.00
    model_config = ConfigDict(extra="allow", frozen=True)


class CommunicationRules(BaseModel):
    """component of Persona model"""

    avoid: List[str]
    model_config = ConfigDict(extra="allow", frozen=True)


class Persona(BaseModel):
    """model for project stakeholder agent persona
    uses sub-models defined above
    """

    name: str
    role: str
    location: str
    background: List[str]
    goals: List[str]
    expertise_level: ExpertiseLevel
    personality: Personality
    communication_rules: CommunicationRules
    model_config = ConfigDict(extra="allow", frozen=True)
