"""
InstructionsModel

Purpose: Primary instructions and rules for dynamic agent sentiment; references other models for cues and scale.
"""

from pydantic import BaseModel
from typing import List, Optional


class InstructionsModel(BaseModel):
    purpose: str
    precedence: bool = True
    references: List[str]
    instructions: List[str]
    notes: Optional[str] = None
