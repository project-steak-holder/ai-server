"""
AgentService: Main service for agentic AI stakeholder simulation.
This service will orchestrate conversation flow,
persistence, persona, project context, and LLM interaction for a project stakeholder agent.
"""

from pydantic import BaseModel
from typing import Optional

from src.adapter.llama_adapter import LlamaAdapter
from src.models.llm_query_model import LlmQuery
from src.models.persona_model import Persona
from src.models.project_model import Project
from src.models.message_model import Message
from src.service.persona_service import PersonaService
from src.service.project_service import ProjectService


class AgentService(BaseModel):
    # loaded from respective services
    persona: Optional[Persona] = None
    project: Optional[Project] = None
    history: Optional[list[Message]] = None

    # received from frontend via controller
    request: Optional[str] = None

    # request body to send to backend LLM
    llm_query: Optional[dict] = None

    # used to persist messages to DB
    conversationID: Optional[str] = None

    # getters
    def get_persona(self) -> Optional[Persona]:
        return self.persona

    def get_project(self) -> Optional[Project]:
        return self.project

    def get_history(self) -> Optional[list[Message]]:
        return self.history

    def get_request(self) -> Optional[str]:
        return self.request

    def get_llm_query(self) -> Optional[dict]:
        return self.llm_query

    def get_conversationID(self) -> Optional[str]:
        return self.conversationID

    # load various context models/data
    def load_persona(self):
        service = PersonaService()
        service.load_persona()
        self.persona = PersonaService.get_persona()

    def load_project(self):
        service = ProjectService()
        service.load_project()
        self.project = ProjectService.get_project()

    # Finish ME !!!!
    def load_history(self, history: list[Message]):
        self.history = history

    def set_request(self, request: str):
        self.request = request

    def set_conversationID(self, conversationID: str):
        self.conversationID = conversationID


    # extract message from request or response
    def extract_message(payload: dict) -> str:
        return payload.get("message", "")


    # validate all context content is present
    def validate_context(self) -> bool:
        return (self.request is not None
                and self.persona is not None
                and self.project is not None
                #and self.history is not None
                )

    # assemble context model for LLM query and serialize to dict
    def build_llm_query(self,
                        request: str,
                        history: list[Message],
                        persona: Persona,
                        project: Project):
        self.llm_query = LlmQuery(
            request=request,
            #history=history,
            persona=persona,
            project=project
        ).model_dump()


    # save to DB via service/repository
    def persist_message(self, message: str) -> Message:
        # build into Message model entity
        msg_obj = Message(
            messageID=None,  # placeholder, replace with actual ID generation logic
            conversationID=self.conversationID,
            content=message
        )

        # Call persistence service/repository
        # to save msg_obj to DB here                <------<<<<<

        return msg_obj


    # call LLM via adapter layer
    # accepts and returns dictionary
    def call_llm(self, llm_query: dict) -> dict:
        response = LlamaAdapter.send_query(self.llm_query)
        return response

    # Main Orchestrator Method
    # receives request payload from controller as dict
    # assembles context from persona, project and persistence(history) service
    # persists both request and response messages via persistence service
    # returns response to controller as dict
    def process_agent_query(self, req_payload: dict) -> dict:
        # extract message from request and store
        self.request = AgentService.extract_message(req_payload)
        # set conversationID from payload
        self.set_conversationID(req_payload.get("conversationID"))
        # persist request message
        self.persist_message(self.request)
        # load context
        self.load_persona()
        self.load_project()
        self.load_history()
        # validate context
        if not self.validate_context():
            return {"error": "missing required context."}
        # build LLM query model
        self.build_llm_query(
            request=self.request,
            history=self.history,
            persona=self.persona,
            project=self.project
        )
        # send request to LLM adapter
        response_dict = self.call_llm(self.llm_query)
        # extract message from response
        response = AgentService.extract_message(response_dict)
        # persist response
        self.persist_message(response)

        return response_dict
