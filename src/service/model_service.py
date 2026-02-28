"""
ModelService: Unified loader and cache for agent context models (persona, project, etc.)
Now uses a registry and cache for extensibility.
"""

import os
import json
from typing import Union

from src.exceptions.context_load_exception import ContextLoadException
from src.schemas.persona_model import Persona
from src.schemas.project_model import Project

# only models listed in registry supported
ModelType = Union[Persona, Project]


class ModelService:
    """
    Loads and caches models (persona, project, etc.) for agent context.
    Uses a registry for configuration and a cache for loaded models.
    Supports environment variable overrides for file paths.
    """

    def __init__(self):
        # Registry: model_name -> dict with schema, env_var, default_path
        self._registry = {
            "persona": {
                "schema": Persona,
                "env_var": "PERSONA_FILE",
                "default_path": "data/persona.json",
            },
            "project": {
                "schema": Project,
                "env_var": "PROJECT_FILE",
                "default_path": "data/project.json",
            },
            # Add new models here as needed
        }
        # Cache: model_name -> loaded model instance
        self._cache = {}

    def load_model(self, model_name: str) -> ModelType:
        """
        Loads and caches the model instance for the given name.
        Args:
            model_name: e.g. 'persona', 'project', etc.
        Returns:
            The loaded and validated model instance
        """
        if model_name in self._cache:
            return self._cache[model_name]
        if model_name not in self._registry:
            raise ContextLoadException(
                message=f"Unknown model name: {model_name}",
                details={"model_name": model_name},
            )
        entry = self._registry[model_name]
        schema = entry["schema"]
        env_var = entry["env_var"]
        default_path = entry["default_path"]
        file_path = os.environ.get(env_var) or default_path
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            model_instance = schema(**data)
            self._cache[model_name] = model_instance
            return model_instance
        except FileNotFoundError as e:
            raise ContextLoadException(
                message=f"{model_name.capitalize()} file not found: {file_path}",
                details={"exception": str(e)},
            ) from e
        except json.JSONDecodeError as e:
            raise ContextLoadException(
                message=f"Failed to decode {model_name} JSON file",
                details={"exception": str(e), "file_path": file_path},
            ) from e
        except Exception as e:
            raise ContextLoadException(
                message=f"Unexpected error loading {model_name} context",
                details={"exception": str(e), "file_path": file_path},
            ) from e

    def get_model(self, model_name: str) -> ModelType:
        """
        Returns the cached model instance, or loads it if not loaded.
        Args:
            model_name: e.g. 'persona', 'project', etc.
        Returns:
            The cached or newly loaded model instance
        """
        if model_name in self._cache:
            return self._cache[model_name]
        return self.load_model(model_name)

    def list_models(self):
        """Returns a list of all registered model names."""
        return list(self._registry.keys())
