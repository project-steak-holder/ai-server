"""
Project Steak-Holder
Requirement model

used in the project model

contains:
- project name
- business summary
- list of requirements
"""

from pydantic import BaseModel

class Requirement(BaseModel):
    id: str
    category: str
    requirement: str