"""
SentimentScale model

Purpose: Translate between numerical sentiment score and persona-guiding sentiment verb.
"""

from pydantic import BaseModel
from typing import List


class SentimentScaleEntry(BaseModel):
    score: int
    label: str


class SentimentScale(BaseModel):
    purpose: str
    scale: List[SentimentScaleEntry]
