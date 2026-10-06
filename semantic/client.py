"""LLM client abstractions for local and API-based models (Ollama, OpenAI-compatible, Mock)."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import httpx


class BaseLLMClient(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def complete(self, messages: Dict[str, str]) -> str:
        """Send chat messages and return completion response text."""
        pass


class MockLLMClient(BaseLLMClient):
    """Deterministic mock client for offline tests and fallback execution."""

    def __init__(self, canned_responses: Optional[Dict[str, str]] = None):
        self.canned_responses = canned_responses or {}

    def complete(self, messages: Dict[str, str]) -> str:
        user_content = messages.get("user", "")

        # Check canned responses
        for key, response in self.canned_responses.items():
            if key.lower() in user_content.lower():
                return response

        # Default heuristic mock behavior:
        # If candidate list is found in prompt, select first candidate
        for line in user_content.splitlines():
            line_s = line.strip()
            if line_s.startswith("1. "):
                return line_s[3:].strip()

        return ""


class OpenAICompatibleClient(BaseLLMClient):
    """Client for Ollama, vLLM, LM Studio, and OpenAI-compatible endpoints."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        api_key: str = "ollama",
        model: str = "llama3.2",
        temperature: float = 0.0,
        timeout: float = 15.0,
        client: Optional[httpx.Client] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self._client = client

    def _get_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        return httpx.Client(timeout=self.timeout, headers=headers)

    def complete(self, messages: Dict[str, str]) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": messages.get("system", "")},
                {"role": "user", "content": messages.get("user", "")},
            ],
        }

        client = self._get_client()
        try:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices and "message" in choices[0]:
                    return choices[0]["message"].get("content", "").strip()
            return ""
        except Exception:
            return ""
        finally:
            if self._client is None:
                client.close()


def create_llm_client(config: Dict[str, Any]) -> BaseLLMClient:
    """Factory to instantiate LLM client based on configuration."""
    provider = config.get("provider", "mock").lower()

    if provider in ["ollama", "openai", "openai_compatible"]:
        return OpenAICompatibleClient(
            base_url=config.get("base_url", "http://localhost:11434/v1"),
            api_key=config.get("api_key", "ollama"),
            model=config.get("model", "llama3.2"),
            temperature=float(config.get("temperature", 0.0)),
            timeout=float(config.get("timeout", 15.0)),
        )
    return MockLLMClient()
