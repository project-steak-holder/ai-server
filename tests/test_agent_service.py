"""
Project Steak-Holder

unit tests for agent_service
"""

from src.service.agent_service import AgentService
from src.service.persona_service import PersonaService
from src.service.project_service import ProjectService

from src.models.persona_model import Persona
from src.models.project_model import Project
from src.models.message_model import Message
from src.models.llm_query_model import LlmQuery



# test loading persona from service / default file
def test_load_persona(monkeypatch):
    # make sure environment variable not set -> default file used
    monkeypatch.delenv("PERSONA_FILE", raising=False)
    agent = AgentService()
    agent.load_persona()
    assert isinstance(agent.persona, Persona)
    assert agent.persona.name == "Owen"
    assert agent.persona.role == "Owner, Golden Bikes"



# test loading project from service / default file
def test_load_project(monkeypatch):
    # make sure environment variable not set -> default file used
    monkeypatch.delenv("PROJECT_FILE", raising=False)
    agent = AgentService()
    agent.load_project()
    assert isinstance(agent.project, Project)
    assert agent.project.project_name == "Golden Bikes Rental System"


# will need updating!!!
# test loading history
def test_load_history():
    agent = AgentService()
    history = [
        Message(messageID="M1", conversationID="C3", content="test message 1"),
        Message(messageID="M2", conversationID="C3", content="test message 2")
    ]
    agent.load_history(history)
    assert agent.history == history


# will need updating!!!
# test capturing request
def test_set_request():
    agent = AgentService()
    request = "What are the project requirements?"
    agent.set_request(request)
    assert agent.request == request



# test validating context -> should fail assertions if any context missing
def test_validate_context():
    agent = AgentService()

    # no context set -> should be false
    assert not agent.validate_context()

    # set only request -> should be false
    agent.set_request("What are the project requirements?")
    assert not agent.validate_context()

    # set persona -> should still be false (project + history missing)
    agent.load_persona()
    assert not agent.validate_context()

    # set project -> should be false (history missing)
    agent.load_project()
    assert not agent.validate_context()

    # set history -> should be false
    history = [
        Message(messageID="M1", conversationID="C3", content="test message 1"),
        Message(messageID="M2", conversationID="C3", content="test message 2")
    ]
    agent.load_history(history)
    # now all context set -> should be true
    assert agent.validate_context()



# test building llm query -> should include all 4 context components
def test_build_llm_query(monkeypatch):
    # make sure environment variables not set -> default files used
    monkeypatch.delenv("PERSONA_FILE", raising=False)
    monkeypatch.delenv("PROJECT_FILE", raising=False)

    # set up agent with all context
    agent = AgentService()
    agent.load_persona()
    agent.load_project()

    history = [
        Message(messageID="M1", conversationID="C3", content="test message 1"),
        Message(messageID="M2", conversationID="C3", content="test message 2")
    ]
    agent.load_history(history)
    agent.set_request("What are the project requirements?")

    # build query
    agent.build_llm_query(agent.request, agent.history, agent.persona, agent.project)

    # should have built llm query with all context
    assert isinstance(agent.llm_query, LlmQuery)
    assert agent.llm_query.request == "What are the project requirements?"
    assert agent.llm_query.persona.name == "Owen"
    assert agent.llm_query.project.project_name == "Golden Bikes Rental System"
    assert agent.llm_query.history is not None


# will need updating once DB implemented
# test persisting message to DB
def test_persist_message():
    pass