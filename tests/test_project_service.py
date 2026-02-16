"""
Project Steak-Holder

unit tests for project_service
"""
import json
import uuid

from src.service.project_service import ProjectService
from src.models.project_model import Project


def test_init_uses_env_var(monkeypatch):
    """ test setting filepath as env variable
    """
    # set env variable
    monkeypatch.setenv("PROJECT_FILE", "custom/path/project.json")
    service = ProjectService()
    # should use env variable
    assert service.file_path == "custom/path/project.json"



def test_init_uses_default_when_no_env(monkeypatch):
    """ test default filepath used when env variable not set
    """
    # ensure env variable not set
    monkeypatch.delenv("PROJECT_FILE", raising=False)
    service = ProjectService()
    # should default
    assert service.file_path == "data/project.json"



def test_load_project_default(monkeypatch):
    """ test loading project from default file
    """
    # ensure env variable not set -> default file used
    monkeypatch.delenv("PROJECT_FILE", raising=False)
    service = ProjectService()
    project = service.load_project()

    assert isinstance(project, Project)
    assert project.project_name == "Golden Bikes Rental System"



def test_load_project_from_file(monkeypatch, tmp_path):
    """ test loading project from custom file path set in env variable
    """
    # test project
    project_data = {
        "project_name": "Test Project",
        "business_summary": "Test Business Summary",
        "requirements": [
            {
                "id": str(uuid.uuid4()),
                "category": "Test Requirement",
                "requirement": "Test Requirement 1"
            },
            {
                "id": str(uuid.uuid4()),
                "category": "Test Requirement",
                "requirement": "Test Requirement 2"
            }
        ]
    }
    file_path = tmp_path / "project.json"
    # save to temp file
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(project_data, f)
    # set env variable to temp file path
    monkeypatch.setenv("PROJECT_FILE", str(file_path))
    service = ProjectService()
    project = service.load_project()
    assert project.project_name == "Test Project"
    assert len(project.requirements) == 2



def test_get_project():
    """ test get_project returns loaded project
    """
    service = ProjectService()
    project = service.load_project()
    assert service.get_project() == project
    assert service.get_project().project_name == "Golden Bikes Rental System"