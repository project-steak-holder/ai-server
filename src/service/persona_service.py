"""
Project Steak-Holder
Persona Service

loads agent persona for agent context
default: loads persona from /data/persona.json
can be overridden with "PERSONA_FILE" environment variable
"""

import os
import json
from typing import Optional
from src.models.persona_model import Persona

class PersonaService:

    persona: Optional[Persona] = None

    def __init__(self):
        # override with environment variable or default to /data/persona.json or
        self.file_path = (os.environ.get("PERSONA_FILE")
                          or "data/persona.json")


    # loads persona from file path set in init
    def load_persona(self) -> Persona:
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        PersonaService.persona = Persona(**data)
        return PersonaService.persona


    # fetch persona from service
    @staticmethod
    def get_persona() -> Optional[Persona]:
        return PersonaService.persona
