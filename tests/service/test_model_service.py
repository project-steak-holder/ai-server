"""
Project Steak-Holder

tests for ModelService (unified persona/project loader)
DRYly parameterized to accept new model types (add new model type to MODEL_PARAMS)
"""

import pytest
from unittest.mock import patch
from src.exceptions.context_load_exception import ContextLoadException
from src.service.model_service import ModelService
from src.schemas.persona_model import Persona
from src.schemas.project_model import Project
import uuid

# Model test parameters: (model_name, schema, env_var, default_path, minimal_valid_data)
MODEL_PARAMS = [
    (
        "persona",
        Persona,
        "PERSONA_FILE",
        "data/persona.json",
        {
            "name": "Test Persona",
            "role": "Test Role",
            "location": "Test Location",
            "background": ["Test Background"],
            "goals": ["Goal 1"],
            "expertise_level": {"business": "b", "technology": "t"},
            "personality": {
                "tone": ["t"],
                "professionalism": "p",
                "focus": {"can_tangent": True, "refocus_easily": False},
            },
            "communication_rules": {"avoid": ["a"]},
        },
    ),
    (
        "project",
        Project,
        "PROJECT_FILE",
        "data/project.json",
        {
            "project_name": "Test Project",
            "business_summary": "A summary",
            "requirements": [
                {"id": str(uuid.uuid4()), "category": "cat", "requirement": "req"}
            ],
        },
    ),
]


@pytest.mark.parametrize(
    "model_name,schema,env_var,default_path,minimal_valid_data", MODEL_PARAMS
)
def test_load_model_default(
    monkeypatch, tmp_path, model_name, schema, env_var, default_path, minimal_valid_data
):
    monkeypatch.delenv(env_var, raising=False)
    # Write minimal valid data to the default path expected by the registry
    file_path = tmp_path / default_path.split("/")[-1]
    import json

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(minimal_valid_data, f)
    # Patch the default path in the registry to point to our temp file
    orig_init = ModelService.__init__

    def patched_init(self):
        orig_init(self)
        self._registry[model_name]["default_path"] = str(file_path)

    ModelService.__init__ = patched_init
    service = ModelService()
    result = service.load_model(model_name)
    assert isinstance(result, schema)
    ModelService.__init__ = orig_init


@pytest.mark.parametrize(
    "model_name,schema,env_var,default_path,minimal_valid_data", MODEL_PARAMS
)
def test_load_model_env_var(
    monkeypatch, tmp_path, model_name, schema, env_var, default_path, minimal_valid_data
):
    file_path = tmp_path / f"{model_name}.json"
    import json

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(minimal_valid_data, f)
    monkeypatch.setenv(env_var, str(file_path))
    service = ModelService()
    result = service.load_model(model_name)
    assert isinstance(result, schema)


@pytest.mark.parametrize(
    "model_name,schema,env_var,default_path,minimal_valid_data", MODEL_PARAMS
)
def test_model_caching(
    monkeypatch, tmp_path, model_name, schema, env_var, default_path, minimal_valid_data
):
    file_path = tmp_path / f"{model_name}.json"
    import json

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(minimal_valid_data, f)
    monkeypatch.setenv(env_var, str(file_path))
    service = ModelService()
    obj1 = service.load_model(model_name)
    obj2 = service.get_model(model_name)
    assert obj1 is obj2


@pytest.mark.parametrize("model_name,schema,env_var,default_path,_", MODEL_PARAMS)
def test_model_service_error_paths(
    monkeypatch, tmp_path, model_name, schema, env_var, default_path, _
):
    service = ModelService()
    # File not found
    monkeypatch.setenv(env_var, str(tmp_path / "missing.json"))
    with pytest.raises(
        ContextLoadException, match=f"{model_name.capitalize()} file not found"
    ):
        service.load_model(model_name)
    # Bad JSON
    bad_json = tmp_path / f"bad_{model_name}.json"
    bad_json.write_text("{", encoding="utf-8")
    monkeypatch.setenv(env_var, str(bad_json))
    with pytest.raises(
        ContextLoadException, match=f"Failed to decode {model_name} JSON file"
    ):
        service.load_model(model_name)
    # Unexpected error
    monkeypatch.setenv(env_var, "ignored.json")
    with patch("builtins.open", side_effect=PermissionError("denied")):
        with pytest.raises(
            ContextLoadException, match=f"Unexpected error loading {model_name} context"
        ):
            service.load_model(model_name)
    # Not loaded error (simulate by clearing model)
    with pytest.raises(ContextLoadException, match="Unknown model name"):
        service.get_model("unknown")
