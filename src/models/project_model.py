"""
Project Steak-Holder
Project model

can be overridden by applying another project
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
    """ model for project stakeholder project details
    """
    project_name: str
    business_summary: str
    requirements: List[Requirement]

