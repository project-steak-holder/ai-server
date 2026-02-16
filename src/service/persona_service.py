"""
Project Steak-Holder
Persona Service
"""

import os
import json
from typing import Optional
from src.schemas.persona_model import Persona

from src.exceptions.context_load_exception import ContextLoadException


class PersonaService:
    """loads agent persona for agent context
    default: loads persona from /data/persona.json
    can be overridden with "PERSONA_FILE" environment variable
    """

    persona: Optional[Persona] = None

    def __init__(self):
        """override file with environment variable
        or default to /data/persona.json
        """
        self.file_path = os.environ.get("PERSONA_FILE") or "data/persona.json"

    def load_persona(self) -> Persona:
        """loads persona from file path set in init"""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            PersonaService.persona = Persona(**data)
            return PersonaService.persona
        except FileNotFoundError as e:
            raise ContextLoadException(
                message=f"Persona file not found: {self.file_path}",
                details={"exception": str(e)},
            ) from e
        except json.JSONDecodeError as e:
            raise ContextLoadException(
                message="Failed to decode persona JSON file",
                details={"exception": str(e), "file_path": self.file_path},
            ) from e
        except Exception as e:
            raise ContextLoadException(
                message="Unexpected error loading persona context",
                details={"exception": str(e), "file_path": self.file_path},
            ) from e

    @staticmethod
    def get_persona() -> Persona:
        """fetch persona from service"""
        if PersonaService.persona is None:
            raise ContextLoadException(
                message="Persona not loaded",
                details={"suggestion": "Call load_persona() before getting persona"},
            )
        return PersonaService.persona
