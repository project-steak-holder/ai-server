"""
ModelService: Unified loader and cache for agent context models (persona, project, etc.)
Now uses a registry and cache for extensibility.
"""

import os
import json
from typing import Union, TypedDict, Type, overload
from pydantic import ValidationError

from src.exceptions.context_load_exception import ContextLoadException
from src.schemas.persona_model import Persona
from src.schemas.project_model import Project
from src.schemas.sentiment_scale_model import SentimentScale
from src.schemas.listening_cues_model import ListeningCues
from src.schemas.instructions_model import InstructionsModel
from src.middlewares.events import wide_event

# only models listed in registry supported
ModelType = Union[Persona, Project, SentimentScale, ListeningCues, InstructionsModel]


# TypedDict for registry entries
class ModelRegistryEntry(TypedDict):
    schema: Type[ModelType]
    env_var: str
    default_path: str


class ModelService:
    """
    Loads and caches models (persona, project, etc.) for agent context.
    Uses a registry for configuration and a cache for loaded models.
    Supports environment variable overrides for file paths.
    """

    # Cache: model_name -> loaded model instance (class-level)
    _cache: dict[str, ModelType] = {}

    def __init__(self):
        # Registry: model_name -> ModelRegistryEntry
        self._registry: dict[str, ModelRegistryEntry] = {
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
            "sentiment_scale": {
                "schema": SentimentScale,
                "env_var": "SENTIMENT_SCALE_FILE",
                "default_path": "data/sentiment_scale.json",
            },
            "listening_cues": {
                "schema": ListeningCues,
                "env_var": "LISTENING_CUES_FILE",
                "default_path": "data/listening_cues.json",
            },
            "instructions": {
                "schema": InstructionsModel,
                "env_var": "INSTRUCTIONS_FILE",
                "default_path": "data/instructions.json",
            },
            # Add new models here as needed
        }

    @wide_event("_load_model")
    def _load_model(self, model_name: str) -> bool:
        """
        (Private) Force reloads / caches a model instance for given name, always reading from disk.
        method ignores cached value / updates cache with newly loaded model.
        Args:
            model_name: e.g. 'persona', 'project', etc.
        Returns:
            True -> if model successfully reloaded and cached.
        Raises:
            ContextLoadException: If the model cannot be loaded or validated.
        """
        if model_name not in self._registry:
            raise ContextLoadException(message=f"Unknown model name: {model_name}")
        entry = self._registry[model_name]
        schema = entry["schema"]
        env_var = entry["env_var"]
        default_path = entry["default_path"]
        file_path = os.environ.get(env_var) or default_path
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            model_instance = schema.model_validate(data)
            # Always update the cache with the new instance
            self.__class__._cache[model_name] = model_instance
            return True
        except FileNotFoundError as fnfe:
            raise ContextLoadException(
                message=f"{model_name.capitalize()} file not found: {file_path}"
            ) from fnfe
        except json.JSONDecodeError as jde:
            raise ContextLoadException(
                message=f"Failed to decode {model_name} JSON file"
            ) from jde
        except ValidationError as ve:
            raise ContextLoadException(
                message=f"Validation error loading {model_name} context"
            ) from ve
        except Exception as cle:
            raise ContextLoadException(
                message=f"Unexpected error loading {model_name} context"
            ) from cle

    @overload
    def get_model[T: ModelType](self, model_name: str, expected_type: Type[T]) -> T: ...
    @overload
    def get_model(self, model_name: str) -> ModelType: ...

    @wide_event("get_model")
    def get_model[T: ModelType](
        self, model_name: str, expected_type: Type[T] | None = None
    ) -> ModelType | T:
        """
        Returns cached model instance, lazy loads as needed.
        If expected_type is provided, validates the type and returns it narrowed.
        """
        if model_name not in self.__class__._cache:
            self._load_model(model_name)
        result = self.__class__._cache[model_name]
        if expected_type is not None and not isinstance(result, expected_type):
            raise TypeError(
                f"Expected {expected_type.__name__}, got {type(result).__name__}"
            )
        return result

    def list_models(self) -> list[str]:
        """Returns a list of all registered model names."""
        return list(self._registry.keys())
