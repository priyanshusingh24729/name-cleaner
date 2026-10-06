"""Unit tests for LLM client implementations (Mock and OpenAI-compatible)."""

import pytest
import httpx
from semantic.client import MockLLMClient, OpenAICompatibleClient, create_llm_client


def test_mock_client_canned_responses():
    """Verify MockLLMClient returns canned response when matched."""
    client = MockLLMClient(canned_responses={"H2OMAP": "H2OMAP Water"})
    messages = {"user": "Resolve: TS-H2OMAP Water 7"}
    assert client.complete(messages) == "H2OMAP Water"


def test_mock_client_fallback_to_candidate():
    """Verify MockLLMClient picks top candidate when no canned response is configured."""
    client = MockLLMClient()
    messages = {
        "user": "RAW APPLICATION NAME: Tool 1.0\nCANDIDATE HYPOTHESES:\n  1. Tool\n  2. Tool 1.0"
    }
    assert client.complete(messages) == "Tool"


def test_openai_compatible_client_success():
    """Verify OpenAICompatibleClient parses chat completions response."""
    def handler(request: httpx.Request):
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": "AutoCAD"}}
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)

    client = OpenAICompatibleClient(
        base_url="http://mock-llm:11434/v1",
        client=http_client,
    )
    result = client.complete({"system": "System", "user": "User"})
    assert result == "AutoCAD"


def test_create_llm_client_factory():
    """Verify factory returns appropriate client class based on provider."""
    mock_client = create_llm_client({"provider": "mock"})
    assert isinstance(mock_client, MockLLMClient)

    api_client = create_llm_client({
        "provider": "ollama",
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
    })
    assert isinstance(api_client, OpenAICompatibleClient)
