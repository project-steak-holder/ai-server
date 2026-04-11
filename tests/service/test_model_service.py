"""
Project Steak-Holder

tests for ModelService (unified persona/project loader)
DRYly parameterized to accept new model types (add new model type to MODEL_PARAMS)
"""

import pytest
from unittest.mock import patch
from src.exceptions.context_load_exception import ContextLoadException
from src.service.model_service import ModelService
import json


def test_load_model_default_persona(monkeypatch, tmp_path, sample_persona):
    model_name = "persona"
    schema = type(sample_persona)
    env_var = "PERSONA_FILE"
    default_path = "data/persona.json"
    minimal_valid_data = sample_persona.model_dump()
    monkeypatch.delenv(env_var, raising=False)
    file_path = tmp_path / default_path.split("/")[-1]

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(minimal_valid_data, f)
    orig_init = ModelService.__init__

    def patched_init(self):
        orig_init(self)
        self._registry[model_name]["default_path"] = str(file_path)

    monkeypatch.setattr(ModelService, "__init__", patched_init)
    service = ModelService()
    result = service._load_model(model_name)
    assert result is True
    loaded = service.get_model(model_name)
    assert isinstance(loaded, schema)
    monkeypatch.setattr(ModelService, "__init__", orig_init)


def test_load_model_default_project(monkeypatch, tmp_path, sample_project):
    model_name = "project"
    schema = type(sample_project)
    env_var = "PROJECT_FILE"
    default_path = "data/project.json"
    minimal_valid_data = sample_project.model_dump()
    monkeypatch.delenv(env_var, raising=False)
    file_path = tmp_path / default_path.split("/")[-1]

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(minimal_valid_data, f)
    orig_init = ModelService.__init__

    def patched_init(self):
        orig_init(self)
        self._registry[model_name]["default_path"] = str(file_path)

    monkeypatch.setattr(ModelService, "__init__", patched_init)
    service = ModelService()
    result = service._load_model(model_name)
    assert result is True
    loaded = service.get_model(model_name)
    assert isinstance(loaded, schema)
    monkeypatch.setattr(ModelService, "__init__", orig_init)


def test_load_model_env_var_persona(monkeypatch, tmp_path, sample_persona):
    model_name = "persona"
    schema = type(sample_persona)
    env_var = "PERSONA_FILE"
    file_path = tmp_path / f"{model_name}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(sample_persona.model_dump(), f)
    monkeypatch.setenv(env_var, str(file_path))
    service = ModelService()
    result = service._load_model(model_name)
    assert result is True
    loaded = service.get_model(model_name)
    assert isinstance(loaded, schema)


def test_load_model_env_var_project(monkeypatch, tmp_path, sample_project):
    model_name = "project"
    schema = type(sample_project)
    env_var = "PROJECT_FILE"
    file_path = tmp_path / f"{model_name}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(sample_project.model_dump(), f)
    monkeypatch.setenv(env_var, str(file_path))
    service = ModelService()
    result = service._load_model(model_name)
    assert result is True
    loaded = service.get_model(model_name)
    assert isinstance(loaded, schema)


def test_model_caching_persona(monkeypatch, tmp_path, sample_persona):
    model_name = "persona"
    env_var = "PERSONA_FILE"
    file_path = tmp_path / f"{model_name}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(sample_persona.model_dump(), f)
    monkeypatch.setenv(env_var, str(file_path))
    service = ModelService()
    result = service._load_model(model_name)
    assert result is True
    obj2 = service.get_model(model_name)
    assert isinstance(obj2, type(sample_persona))


def test_model_caching_project(monkeypatch, tmp_path, sample_project):
    model_name = "project"
    env_var = "PROJECT_FILE"
    file_path = tmp_path / f"{model_name}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(sample_project.model_dump(), f)
    monkeypatch.setenv(env_var, str(file_path))
    service = ModelService()
    result = service._load_model(model_name)
    assert result is True
    obj2 = service.get_model(model_name)
    assert isinstance(obj2, type(sample_project))


def test_model_service_error_paths(monkeypatch, tmp_path):
    # Clear the model cache to ensure error paths are tested
    from src.service.model_service import ModelService

    ModelService._cache.clear()
    service = ModelService()
    model_name = "persona"
    env_var = "PERSONA_FILE"
    # File not found
    monkeypatch.setenv(env_var, str(tmp_path / "missing.json"))
    with pytest.raises(
        ContextLoadException, match=f"{model_name.capitalize()} file not found"
    ):
        service._load_model(model_name)
    # Bad JSON
    bad_json = tmp_path / f"bad_{model_name}.json"
    bad_json.write_text("{", encoding="utf-8")
    monkeypatch.setenv(env_var, str(bad_json))
    with pytest.raises(
        ContextLoadException, match=f"Failed to decode {model_name} JSON file"
    ):
        service._load_model(model_name)
    # Unexpected error
    monkeypatch.setenv(env_var, "ignored.json")
    with patch("builtins.open", side_effect=PermissionError("denied")):
        with pytest.raises(
            ContextLoadException, match=f"Unexpected error loading {model_name} context"
        ):
            service._load_model(model_name)
    # Not loaded error (simulate by clearing model)
    with pytest.raises(ContextLoadException, match="Unknown model name"):
        service.get_model("unknown")
    model_name = "project"
    env_var = "PROJECT_FILE"
    # File not found
    monkeypatch.setenv(env_var, str(tmp_path / "missing.json"))
    with pytest.raises(
        ContextLoadException, match=f"{model_name.capitalize()} file not found"
    ):
        service._load_model(model_name)
    # Bad JSON
    bad_json = tmp_path / f"bad_{model_name}.json"
    bad_json.write_text("{", encoding="utf-8")
    monkeypatch.setenv(env_var, str(bad_json))
    with pytest.raises(
        ContextLoadException, match=f"Failed to decode {model_name} JSON file"
    ):
        service._load_model(model_name)
    # Unexpected error
    monkeypatch.setenv(env_var, "ignored.json")
    with patch("builtins.open", side_effect=PermissionError("denied")):
        with pytest.raises(
            ContextLoadException, match=f"Unexpected error loading {model_name} context"
        ):
            service._load_model(model_name)
    # Not loaded error (simulate by clearing model)
    with pytest.raises(ContextLoadException, match="Unknown model name"):
        service.get_model("unknown")


# Canonical test data for persona and project is now provided by sample_persona and sample_project fixtures in conftest.py.
