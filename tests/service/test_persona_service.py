"""
Project Steak-Holder

unit tests for persona_service
"""

import json
from unittest.mock import patch

import pytest

from src.exceptions.context_load_exception import ContextLoadException
from src.service.persona_service import PersonaService
from src.schemas.persona_model import Persona


def test_init_uses_env_var(monkeypatch):
    """test setting filepath as env variable"""
    # set env variable
    monkeypatch.setenv("PERSONA_FILE", "custom/path/persona.json")
    service = PersonaService()
    # should use env variable
    assert service.file_path == "custom/path/persona.json"


def test_init_uses_default_when_no_env(monkeypatch):
    """test default filepath used when env variable not set"""
    # ensure env variable not set
    monkeypatch.delenv("PERSONA_FILE", raising=False)
    service = PersonaService()
    # should default
    assert service.file_path == "data/persona.json"


def test_load_persona_default(monkeypatch):
    """test loading persona from default file"""
    # ensure env variable not set -> default file used
    monkeypatch.delenv("PERSONA_FILE", raising=False)
    service = PersonaService()
    persona = service.load_persona()

    assert isinstance(persona, Persona)
    assert persona.role == "Owner, Golden Bikes"


def test_load_persona_from_file(monkeypatch, tmp_path):
    """test loading persona from custom file path set in env variable"""
    # create test persona file
    persona_data = {
        "name": "Test Persona",
        "role": "Test Role",
        "location": "Test Location",
        "background": ["Test Background"],
        "goals": ["Goal 1", "Goal 2"],
        "expertise_level": {
            "business": "Test Business Expertise",
            "technology": "Test Technology Expertise",
        },
        "personality": {
            "tone": ["Test Tone"],
            "professionalism": "Test Professionalism",
            "focus": {"can_tangent": True, "refocus_easily": False},
        },
        "communication_rules": {"avoid": ["Test Avoid 1", "Test Avoid 2"]},
    }
    file_path = tmp_path / "persona.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(persona_data, f)
    # set env variable to temp file path
    monkeypatch.setenv("PERSONA_FILE", str(file_path))
    service = PersonaService()
    persona = service.load_persona()
    assert isinstance(persona, Persona)
    assert persona.role == "Test Role"


def test_get_persona():
    """test get_persona returns loaded persona"""
    service = PersonaService()
    persona = service.load_persona()
    assert service.get_persona() == persona
    assert service.get_persona().role == "Owner, Golden Bikes"


def test_persona_service_error_paths(monkeypatch, tmp_path):
    """test persona service exception branches"""
    PersonaService.persona = None
    monkeypatch.setenv("PERSONA_FILE", str(tmp_path / "missing.json"))
    with pytest.raises(ContextLoadException, match="Persona file not found"):
        PersonaService().load_persona()

    bad_json = tmp_path / "bad_persona.json"
    bad_json.write_text("{", encoding="utf-8")
    monkeypatch.setenv("PERSONA_FILE", str(bad_json))
    with pytest.raises(
        ContextLoadException, match="Failed to decode persona JSON file"
    ):
        PersonaService().load_persona()

    monkeypatch.setenv("PERSONA_FILE", "ignored.json")
    with patch("builtins.open", side_effect=PermissionError("denied")):
        with pytest.raises(
            ContextLoadException, match="Unexpected error loading persona context"
        ):
            PersonaService().load_persona()

    PersonaService.persona = None
    with pytest.raises(ContextLoadException, match="Persona not loaded"):
        PersonaService.get_persona()
