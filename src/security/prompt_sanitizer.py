"""
Shared prompt-sanitization helpers for defending LLM prompts against
injection attacks from untrusted user or model content.
"""

import re
from functools import lru_cache


DEFAULT_PROMPT_TAGS: tuple[str, ...] = ("transcript", "previous_summary")


@lru_cache(maxsize=8)
def _compile_tag_pattern(tags: tuple[str, ...]) -> re.Pattern[str]:
    alternation = "|".join(re.escape(t) for t in tags)
    return re.compile(rf"</?(?:{alternation})>", re.IGNORECASE)


def sanitize_for_prompt(
    text: str,
    tags: tuple[str, ...] = DEFAULT_PROMPT_TAGS,
) -> str:
    """Neutralize XML-like delimiter tokens in untrusted content so it cannot
    break out of its structural envelope in an LLM prompt.

    For each tag in `tags`, replaces occurrences of `<tag>` or `</tag>`
    (case-insensitive) with a visibly-escaped square-bracket form. Content is
    preserved verbatim apart from this framing neutralization, so the summary
    still sees what the user/AI actually said.
    """
    pattern = _compile_tag_pattern(tags)
    return pattern.sub(
        lambda m: m.group().replace("<", "[").replace(">", "]"),
        text,
    )
