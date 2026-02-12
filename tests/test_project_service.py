"""
Project Steak-Holder

unit tests for project_service
"""
import json

from src.service.project_service import ProjectService
from src.models.project_model import Project


# test setting filepath as env variable
def test_init_uses_env_var(monkeypatch):
    # set env variable
    monkeypatch.setenv("PROJECT_FILE", "custom/path/project.json")
    service = ProjectService()
    # should use env variable
    assert service.file_path == "custom/path/project.json"



# test default filepath used when env variable not set
def test_init_uses_default_when_no_env(monkeypatch):
    # ensure env variable not set
    monkeypatch.delenv("PROJECT_FILE", raising=False)
    service = ProjectService()
    # should default
    assert service.file_path == "data/project.json"



# test loading project from default file
def test_load_project_default(monkeypatch):
    # ensure env variable not set -> default file used
    monkeypatch.delenv("PROJECT_FILE", raising=False)
    service = ProjectService()
    project = service.load_project()

    assert isinstance(project, Project)
    assert project.project_name == "Golden Bikes Rental System"



# test loading project from custom file path set in env variable
def test_load_project_from_file(monkeypatch, tmp_path):
    # test project
    project_data = {
        "project_name": "Test Project",
        "business_summary": "Test Business Summary",
        "requirements": [
            {
                "id": "A1",
                "category": "Test Requirement",
                "requirement": "Test Requirement 1"
            },
            {
                "id": "B2",
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
    assert isinstance(project, Project)
    assert project.business_summary == "Test Business Summary"



# test get_project returns loaded project
def test_get_project(monkeypatch):
    service = ProjectService()
    project = service.load_project()
    assert service.get_project() == project
    assert service.get_project().project_name == "Golden Bikes Rental System"