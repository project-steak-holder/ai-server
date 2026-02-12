"""
Project Steak-Holder
Project Service

loads project scenario for agent context
default: loads from /data/project.json
can be overridden with "PROJECT_FILE" environment variable
"""

import os
import json
from typing import Optional
from src.models.project_model import Project

class ProjectService:

    project: Optional[Project] = None


    def __init__(self):
        # override with environment variable or default to /data/project.json or
        self.file_path = (os.environ.get("PROJECT_FILE")
                          or "data/project.json")


    # loads project from file path set in init
    def load_project(self) -> Project:
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ProjectService.project = Project(**data)
        return ProjectService.project


    # fetch project from service
    @staticmethod
    def get_project() -> Optional[Project]:
        return ProjectService.project