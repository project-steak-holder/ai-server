"""
Adapter class for making requests to oLLaMA API for project stakeholder agent.
"""
import requests
from typing import Any, Dict

class LlamaAdapter:
    """ receives llm-query data model from AgentService
        formats it for oLLaMA
        sends request to oLLaMA API
        returns response parsed to a dictionary to AgentService
    """
    # will use env variables
    API_URL = "oLlama_url"  # Placeholder
    API_KEY = "your-api-key"  # Placeholder
    TIMEOUT = 30  # seconds


    @classmethod
    def send_query(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """ sends a query to oLlama API
            accepts a dictionary -> request payload
            returns response as dictionary -> response payload
        """
        headers = {
            "Authorization": f"Bearer {cls.API_KEY}",
            "Content-Type": "application/json"
        }
        response = requests.post(cls.API_URL, json=payload, headers=headers, timeout=cls.TIMEOUT)
        response.raise_for_status()
        return response.json()
