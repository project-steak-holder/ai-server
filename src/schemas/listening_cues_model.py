"""
ListeningCues model

Purpose: Listening cues for evaluating and guiding agent-stakeholder interactions;
cues are grouped by positive and negative categories, each with a cue and score.
"""

from pydantic import BaseModel
from typing import List, Optional, Dict


class ListeningCue(BaseModel):
    cue: str
    score: float
    note: Optional[str] = None


class ListeningCues(BaseModel):
    purpose: str
    outcome: str
    cues: Dict[str, List[ListeningCue]]  # keys: 'positive', 'negative'
