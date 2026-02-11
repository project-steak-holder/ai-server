"""
Project Steak-Holder
Message model

individual message objects retrieved from DB will be saved as Message models

contains:
- messageID
- conversationID
- content
"""

from pydantic import BaseModel

class Message(BaseModel):
    messageID: str
    conversationID: str
    content: str