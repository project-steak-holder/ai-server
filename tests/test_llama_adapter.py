"""
Unit tests for the LLaMA adapter module
"""
from unittest.mock import patch, MagicMock
from src.adapter.llama_adapter import LlamaAdapter

def test_send_query_success():
    # prepare fake payload and expected response
    payload = {"request": "Test message", "persona": {"name": "Test"}, "project": {"project_name": "Test Project"}}
    expected_response = {"message": "LLM response"}

    # Patch 'requests.post' in the llama_adapter module
    with patch("src.adapter.llama_adapter.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = LlamaAdapter.send_query(payload)

        # result matches expected response?
        assert result == expected_response
