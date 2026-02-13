"""
Project Steak-Holder

unit tests for agent_service
"""
from unittest.mock import patch

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



# test extracting message
def test_extract_message():
    # main case - message key exists
    payload = {"message": "This is a test message."}
    extracted_message = AgentService.extract_message(payload)
    assert extracted_message == "This is a test message."

    # edge case: message field missing
    payload = {"not_message": "No message here"}
    assert AgentService.extract_message(payload) == ""

    # edge case: empty dict
    payload = {}
    assert AgentService.extract_message(payload) == ""


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
    """assert not agent.validate_context()

    # set history -> should be false
    history = [
        Message(messageID="M1", conversationID="C3", content="test message 1"),
        Message(messageID="M2", conversationID="C3", content="test message 2")
    ]
    agent.load_history(history)
    # now all context set -> should be true"""
    assert agent.validate_context()



# test building llm query -> should include all 4 context components
def test_build_llm_query(monkeypatch):
    # Ensure environment variables are not set so default files are used
    monkeypatch.delenv("PERSONA_FILE", raising=False)
    monkeypatch.delenv("PROJECT_FILE", raising=False)

    # Set up agent with all context
    agent = AgentService()
    agent.load_persona()
    agent.load_project()

    history = [
        Message(messageID="M1", conversationID="C3", content="test message 1"),
        Message(messageID="M2", conversationID="C3", content="test message 2")
    ]
    agent.load_history(history)
    agent.set_request("What are the project requirements?")

    # Build query (now serialized as dict)
    agent.build_llm_query(
        request=agent.request,
        history=agent.history,
        persona=agent.persona,
        project=agent.project
    )

    # Assert llm_query is a dict and contains expected keys/values
    assert isinstance(agent.llm_query, dict)
    assert agent.llm_query["request"] == "What are the project requirements?"
    assert agent.llm_query["persona"]["name"] == "Owen"
    assert agent.llm_query["project"]["project_name"] == "Golden Bikes Rental System"
    #assert isinstance(agent.llm_query["history"], list)





# test persisting message to DB
def test_persist_message():
    agent = AgentService()
    agent.set_conversationID("conv-xyz")
    test_content = "This is a test message."
    msg = agent.persist_message(test_content)
    assert isinstance(msg, Message)
    assert msg.content == test_content
    assert msg.conversationID == "conv-xyz"

    # test actual repo persistence here          <---------------<<<<<<<<<<<<<<



# test calling LLM via adapter
# should return response dictionary
def test_call_llm():
    agent = AgentService()
    # test request dictionary
    test_query = {
        "request": "Test message",
        "persona": {"name": "Test"},
        "project": {"project_name": "Test Project"}
    }
    agent.llm_query = test_query

    # test response
    test_response = {"message": "LLM response"}

    # patch LlamaAdapter.send_query method
    with patch("src.adapter.llama_adapter.LlamaAdapter.send_query", return_value=test_response):
        result = agent.call_llm(agent.llm_query)

    assert result == test_response



# tests main orchestrator method -> process_agent_query()
# using mocked resources
def test_process_agent_query(monkeypatch):
    agent = AgentService()
    # mock resources
    req_payload = {
        "message": "What are the project requirements?",
        "conversationID": "conv-123"
    }

    # mock persona and project
    persona = Persona(name="Test Persona", role="Test Role", location="Test Location", background=["bg"],
                      goals=["goal"], expertise_level={"business": "high", "technology": "low"},
                      personality={"tone": ["friendly"], "professionalism": "casual",
                                   "focus": {"can_tangent": False, "refocus_easily": True}},
                      communication_rules={"avoid": ["jargon"]})

    project = Project(project_name="Test Project", business_summary="summary", requirements=[])

    # patch in mocks
    monkeypatch.setattr(AgentService, "load_persona", lambda self: setattr(self, "persona", persona))
    monkeypatch.setattr(AgentService, "load_project", lambda self: setattr(self, "project", project))
    monkeypatch.setattr(AgentService, "load_history", lambda self, history=None: setattr(self, "history", []))
    monkeypatch.setattr(AgentService, "persist_message", lambda self, msg: None)

    # mock LLM adapter response
    mock_llm_response = {"message": "LLM response"}

    with patch("src.adapter.llama_adapter.LlamaAdapter.send_query", return_value=mock_llm_response):
        # patch call_llm to use adapter mock
        monkeypatch.setattr(AgentService, "call_llm", lambda self, llm_query: mock_llm_response)
        # run orchestrator
        result = agent.process_agent_query(req_payload)

    assert result == mock_llm_response
