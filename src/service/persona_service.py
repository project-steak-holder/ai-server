"""
Project Steak-Holder
Persona Service
"""

import os
import json
from typing import Optional
from src.models.persona_model import Persona

class PersonaService:
    """ loads agent persona for agent context
    default: loads persona from /data/persona.json
    can be overridden with "PERSONA_FILE" environment variable
    """
    persona: Optional[Persona] = None

    def __init__(self):
        """ override file with environment variable
            or default to /data/persona.json
        """
        self.file_path = (os.environ.get("PERSONA_FILE")
                          or "data/persona.json")


    def load_persona(self) -> Persona:
        """ loads persona from file path set in init
        """
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        PersonaService.persona = Persona(**data)
        return PersonaService.persona



    @staticmethod
    def get_persona() -> Optional[Persona]:
        """ fetch persona from service
        """
        return PersonaService.persona
