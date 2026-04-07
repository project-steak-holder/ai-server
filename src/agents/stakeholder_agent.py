"""
Stakeholder Agent using PydanticAI.
Simulates a project stakeholder persona for interactive conversations.
"""

import os
import re
from typing import cast, AsyncGenerator, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, ModelMessage
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.exceptions.llm_response_exception import LlmResponseException
from src.middlewares.events import wide_event
from src.schemas.persona_model import Persona
from src.schemas.project_model import Project
from src.schemas.sentiment_scale_model import SentimentScale
from src.schemas.listening_cues_model import ListeningCues
from src.schemas.instructions_model import InstructionsModel


class AgentDependencies(BaseModel):
    """Dependencies passed to the agent for each run."""

    persona: Persona
    project: Project
    history: list[ModelMessage] = Field(default_factory=list)
    sentiment_scale: "SentimentScale"
    listening_cues: "ListeningCues"
    instructions: "InstructionsModel"


def strip_think_tags(text: str, strip_whitespace: bool = False) -> str:
    """Remove all <think>...</think> tags from the text (non-greedy). Optionally strip whitespace."""
    if not isinstance(text, str):
        return text
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return cleaned.strip() if strip_whitespace else cleaned


class AgentResponse(BaseModel):
    """Structured response from the stakeholder agent."""

    content: str = Field(..., description="The agent's response message")
    sentiment: Optional[float] = Field(
        default=None,
        description="The updated sentiment value after this message, if available.",
    )


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
    @agent.instructions
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

    # nested cast to ensure type safety(safe for mypy in CI/CD pipeline)
    return cast(Agent[AgentDependencies, AgentResponse], cast(object, agent))


# Singleton instance
_agent: Optional[Agent[AgentDependencies, AgentResponse]] = None


def get_stakeholder_agent() -> Agent[AgentDependencies, AgentResponse]:
    """Get or create the stakeholder agent singleton."""
    global _agent
    if _agent is None:
        _agent = create_stakeholder_agent()
    return _agent


@wide_event("stakeholder_query_stream")
async def run_stakeholder_query_stream(
    message: str,
    persona: Persona,
    project: Project,
    history: list[ModelMessage],
    sentiment_scale: SentimentScale,
    listening_cues: ListeningCues,
    instructions: InstructionsModel,
) -> AsyncGenerator[str, None]:
    """Yield text chunks directly - maintain layer consistency."""
    agent = get_stakeholder_agent()

    deps = AgentDependencies(
        persona=persona,
        project=project,
        history=history,
        sentiment_scale=sentiment_scale,
        listening_cues=listening_cues,
        instructions=instructions,
    )

    try:
        async with agent.run_stream(
            user_prompt=message, deps=deps, message_history=history, output_type=str
        ) as streamed_result:
            async for chunk in streamed_result.stream_text(delta=True):
                # Clean each chunk before yielding (remove think tags only, preserve whitespace)
                yield strip_think_tags(chunk, strip_whitespace=False)

    except (AttributeError, TypeError, ValueError, RuntimeError) as e:
        raise LlmResponseException(
            message="Error streaming stakeholder agent response",
            details={"error": str(e)},
        )
    except Exception as e:
        raise LlmResponseException(
            message="Unexpected error streaming stakeholder agent response",
            details={"error": str(e)},
        )
