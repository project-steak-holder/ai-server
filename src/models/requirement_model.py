"""
Project Steak-Holder
Requirement model

Used in the Project model,
which stores a list of Requirement objects

contains:
- requirement id
- category
- requirement
"""

from pydantic import BaseModel
import uuid

class Requirement(BaseModel):
    """ used in project model to define project requirements
    """
    id: uuid.UUID
    category: str
    requirement: str