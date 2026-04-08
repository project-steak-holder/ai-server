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
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

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
    model_name = os.environ.get("AI_PROVIDER_MODEL", "gemini-2.5-flash")

    if model_name.startswith("gemini"):
        provider = GoogleProvider(api_key=api_key)
        model = GoogleModel(model_name=model_name, provider=provider)
    else:
        openai_provider = OpenAIProvider(
            base_url=api_base_url,
            api_key=api_key,
        )
        model = OpenAIChatModel(
            model_name=model_name,
            provider=openai_provider,
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
        sentiment_scale = ctx.deps.sentiment_scale
        listening_cues = ctx.deps.listening_cues
        instructions = ctx.deps.instructions

        # Current sentiment context
        current_sentiment = persona.personality.sentiment
        if current_sentiment is not None:
            closest_label = min(
                sentiment_scale.scale,
                key=lambda e: abs(e.score - current_sentiment),
            ).label
            sentiment_context = (
                f"Your current sentiment toward this conversation is {current_sentiment} ({closest_label}).\n"
                "Let this influence your tone and willingness to engage — "
                "a low sentiment means you are frustrated or disengaged, "
                "a high sentiment means you are enthusiastic and cooperative.\n"
            )
        else:
            sentiment_context = "This is the start of the conversation. Your sentiment is neutral (0).\n"

        # Build sentiment scale description
        scale_lines = "\n".join(
            f"  {entry.score}: {entry.label}" for entry in sentiment_scale.scale
        )

        # Build listening cues description
        cue_lines = ""
        for category, cues in listening_cues.cues.items():
            cue_lines += f"\n  {category.capitalize()} cues:\n"
            for cue in cues:
                note_str = f" ({cue.note})" if cue.note else ""
                cue_lines += f"    - {cue.cue} (score: {cue.score}){note_str}\n"

        # Build instructions
        instruction_lines = "\n".join(
            f"  - {inst}" for inst in instructions.instructions
        )
        notes_str = f"\nNotes: {instructions.notes}" if instructions.notes else ""

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
            "Respond naturally as this stakeholder would, considering the conversation history.\n\n"
            "--- SENTIMENT EVALUATION ---\n"
            f"Current Sentiment State:\n{sentiment_context}\n"
            f"{sentiment_scale.purpose}\n"
            f"Sentiment scale:\n{scale_lines}\n\n"
            f"{listening_cues.purpose}\n"
            f"Outcome: {listening_cues.outcome}\n"
            f"Listening cues:{cue_lines}\n"
            f"{instructions.purpose}\n"
            f"Instructions:\n{instruction_lines}\n"
            f"{notes_str}\n\n"
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
) -> AsyncGenerator[AgentResponse, None]:
    """Yield AgentResponse objects as structured output streams in."""
    agent = get_stakeholder_agent()

    deps = AgentDependencies(
        persona=persona,
        project=project,
        history=history,
        sentiment_scale=sentiment_scale,
        listening_cues=listening_cues,
        instructions=instructions,
    )

    prev_content = ""
    try:
        async with agent.run_stream(
            user_prompt=message, deps=deps, message_history=history
        ) as streamed_result:
            async for partial in streamed_result.stream_output(debounce_by=0.05):
                # stream_output yields partial AgentResponse objects as they build up
                # Extract only the new content delta
                current_content = partial.content if partial.content else ""
                delta = current_content[len(prev_content) :]
                prev_content = current_content
                if delta:
                    cleaned = strip_think_tags(delta, strip_whitespace=False)
                    if cleaned:
                        print(cleaned, partial.sentiment)
                        yield AgentResponse(
                            content=cleaned, sentiment=partial.sentiment
                        )

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
