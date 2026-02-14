"""
Project Steak-Holder
Requirement model

used in the project model

contains:
- requirement id
- category
- list of requirements
"""

from pydantic import BaseModel

class Requirement(BaseModel):
    """ used in project model to define project requirements
    """
    id: str
    category: str
    requirement: str