"""
Stakeholder Agent using PydanticAI.
Simulates a project stakeholder persona for interactive conversations.
"""

import os

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.exceptions.llm_response_exception import LlmResponseException
from src.schemas.persona_model import Persona
from src.schemas.project_model import Project
from src.schemas.message_model import Message


class AgentDependencies(BaseModel):
    """Dependencies passed to the agent for each run."""

    persona: Persona
    project: Project
    history: list[Message] = Field(default_factory=list)


class AgentResponse(BaseModel):
    """Structured response from the stakeholder agent."""

    content: str = Field(..., description="The agent's response message")


# Initialize PydanticAI Agent
def create_stakeholder_agent() -> Agent[AgentDependencies, AgentResponse]:
    """Create and configure the stakeholder agent."""

    # Get environment variables
    api_base_url = os.environ.get("AI_PROVIDER_BASE_URL", "")
    api_key = os.environ.get("AI_PROVIDER_API_KEY", "")
    model_name = os.environ.get("AI_PROVIDER_MODEL", "llama3.1:8b")

    provider = OpenAIProvider(
        base_url=api_base_url,
        api_key=api_key,
    )

    model = OpenAIChatModel(
        model_name=model_name,
        provider=provider,
    )

    agent = Agent(
        model=model,
        deps_type=AgentDependencies,
        output_type=AgentResponse,
    )

    # Create agent with system prompt
    @agent.system_prompt
    def stakeholder_system_prompt(ctx: RunContext[AgentDependencies]) -> str:
        persona = ctx.deps.persona
        project = ctx.deps.project

        return (
            f"You are {persona.name}, a {persona.role}.\n\n"
            f"Background: {persona.background}\n"
            f"Goals: {persona.goals}\n"
            f"Expertise: {persona.expertise_level}\n\n"
            f"You are discussing the project: {project.project_name}\n"
            f"Project Summary: {project.business_summary}\n\n"
            "Communicate according to your personality:\n"
            f"- Tone: {persona.personality.tone}\n"
            f"- Professionalism: {persona.personality.professionalism}\n"
            f"- Focus: {persona.personality.focus}\n\n"
            "Communication Rules:\n"
            f"- Avoid: {persona.communication_rules.avoid}\n\n"
            "Respond naturally as this stakeholder would, considering the conversation history."
        )

    return agent


# Singleton instance
_agent: Agent[AgentDependencies, AgentResponse] | None = None


def get_stakeholder_agent() -> Agent[AgentDependencies, AgentResponse]:
    """Get or create the stakeholder agent singleton."""
    global _agent
    if _agent is None:
        _agent = create_stakeholder_agent()
    return _agent


async def run_stakeholder_query(
    message: str,
    persona: Persona,
    project: Project,
    history: list[Message],
) -> str:
    """Run a query through the stakeholder agent."""
    agent = get_stakeholder_agent()

    # Create dependencies
    deps = AgentDependencies(
        persona=persona,
        project=project,
        history=history,
    )

    try:
        result = await agent.run(message, deps=deps)
        return result.output.content
    except Exception as e:
        raise LlmResponseException(
            message="Error running stakeholder agent", details={"error": str(e)}
        )
