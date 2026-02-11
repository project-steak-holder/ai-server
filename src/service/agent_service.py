"""
AgentService: Main service for agentic AI stakeholder simulation.
This service will orchestrate conversation flow,
persistence, persona, project context, and LLM interaction for a project stakeholder agent.
"""

from pydantic import BaseModel
from typing import Optional

from src.models.llm_query_model import LlmQuery
from src.models.persona_model import Persona
from src.models.project_model import Project
from src.models.message_model import Message

class AgentService(BaseModel):

    persona: Optional[Persona] = None
    project: Optional[Project] = None
    history: Optional[list[Message]] = None

    # received from frontend via controller
    request: Optional[str]

    # sent to backend LLM
    llm_query: Optional[LlmQuery] = None

    # getters
    def get_persona(self) -> Optional[Persona]:
        return self.persona

    def get_project(self) -> Optional[Project]:
        return self.project

    def get_history(self) -> Optional[list[Message]]:
        return self.history

    def get_request(self) -> Optional[str]:
        return self.request

    def get_llm_query(self) -> Optional[LlmQuery]:
        return self.llmQuery

    # load various context models/data
    def set_persona(self, persona: Persona):
        self.persona = persona

    def set_project(self, project: Project):
        self.project = project

    def set_history(self, history: list[Message]):
        self.history = history

    def set_request(self, request: str):
        self.request = request


    # validate all context content is present
    def validate_context(self) -> bool:
        return (self.request is not None
                and self.persona is not None
                and self.project is not None
                and self.history is not None)


    # assemble context model for LLM query
    def build_query(self,
                    request: str,
                    history: list[Message],
                    persona: Persona,
                    project: Project):
        self.llm_query = LlmQuery(
            request=request,
            history=history,
            persona=persona,
            project=project)


    # save to DB via service/repository
    def persist_message(self, message: Message):
        pass


    # send query to LLM via adapter layer
    def send_query(self, llm_query: LlmQuery):
        pass



