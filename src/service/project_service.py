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

from src.exceptions.context_load_exception import ContextLoadException

class ProjectService:

    project: Optional[Project] = None


    def __init__(self):
        """ override with environment variable
            or default to /data/project.json
        """
        self.file_path = (os.environ.get("PROJECT_FILE")
                          or "data/project.json")



    def load_project(self) -> Project:
        """ loads project from file path set in init
        """
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            ProjectService.project = Project(**data)
            return ProjectService.project
        except FileNotFoundError as e:
            raise ContextLoadException(
                message=f"Project file not found: {self.file_path}",
                details={"exception": str(e)}
            ) from e
        except json.JSONDecodeError as e:
            raise ContextLoadException(
                message="Failed to decode project JSON file",
                details={"exception": str(e), "file_path": self.file_path}
            ) from e
        except Exception as e:
            raise ContextLoadException(
                message="Unexpected error loading project context",
                details={"exception": str(e), "file_path": self.file_path}
            ) from e



    @staticmethod
    def get_project() -> Optional[Project]:
        """ fetch project from service
        """
        return ProjectService.project