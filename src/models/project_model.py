"""
Project Steak-Holder
Project model

can be overridden by applying another persona
with DI at container launch

contains:
- project name
- business summary
- list of requirements
"""

from pydantic import BaseModel
from typing import List

from src.models.requirement_model import Requirement

class Project(BaseModel):
    project_name: str
    business_summary: str
    requirements: List[Requirement]

