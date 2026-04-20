"""
LLM parser implementations with singleton pattern.
Uses remote Ollama API calls for expense parsing.
"""

import json
import logging
from typing import Optional, Dict, Any

import requests

from .config import (
    OLLAMA_CONFIG,
    EXPENSE_SYSTEM_PROMPT,
    OCR_PROMPT_2,
)
from .json_utils import extract_json_from_text

logger = logging.getLogger(__name__)

_parser_instance: Optional["BaseLLMParser"] = None


class BaseLLMParser:
    """Common interface for all expense parsers."""

    def parse_expense(self, text: str) -> Dict[str, Any]:
        raise NotImplementedError

    def parse_ocr_text(self, ocr_text: str) -> Dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def _extract_json(response: str, fallback_text: str) -> Dict[str, Any]:
        try:
            parsed = extract_json_from_text(response)
            if isinstance(parsed, dict):
                parsed["price"] = int(parsed.get("price", 0))
                return parsed
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to extract JSON from LLM response: %s", e)
        return {"category": "khác", "price": 0, "note": fallback_text}


class OllamaLLMParser(BaseLLMParser):
    """Singleton parser that calls Ollama Chat API."""

    _instance: Optional["OllamaLLMParser"] = None
    _initialized: bool = False

    def __new__(cls) -> "OllamaLLMParser":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self.host = OLLAMA_CONFIG.get("host", "http://localhost:11434").rstrip("/")
        self.api_key = OLLAMA_CONFIG.get("api_key", "")
        self.model = OLLAMA_CONFIG.get("model", "qwen2.5:7b")
        self.timeout_seconds = int(OLLAMA_CONFIG.get("timeout_seconds", 60))

        # Support both local Ollama and cloud gateway style base URLs.
        self.chat_url = (
            f"{self.host}/api/chat"
            if self.host.endswith(":11434") or "localhost" in self.host
            else f"{self.host.rstrip('/')}/api/chat"
        )
        self._initialized = True
        logger.info("Ollama parser initialized model=%s host=%s", self.model, self.host)

    @classmethod
    def get_instance(cls) -> "OllamaLLMParser":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def parse_expense(self, text: str) -> Dict[str, Any]:
        normalized_text = text.strip().lower()
        full_prompt = (
            EXPENSE_SYSTEM_PROMPT + "\n\n" + "[Văn bản cần phân tích]: " + normalized_text
        )
        return self._chat_and_parse(full_prompt, normalized_text)

    def parse_ocr_text(self, ocr_text: str) -> Dict[str, Any]:
        normalized_text = ocr_text.strip()
        full_prompt = OCR_PROMPT_2 + "\n\n" + "[Văn bản OCR]: " + normalized_text
        return self._chat_and_parse(full_prompt, normalized_text)

    def _chat_and_parse(self, full_prompt: str, fallback_text: str) -> Dict[str, Any]:

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": full_prompt}],
            "stream": False,
        }

        try:
            response = requests.post(
                self.chat_url,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            message = data.get("message", {})
            content = (message.get("content") or "").strip()
            return self._extract_json(content, fallback_text)
        except Exception as e:
            logger.error("Ollama API request failed model=%s error=%s", self.model, e, exc_info=True)
            return {"category": "khác", "price": 0, "note": fallback_text}


def get_llm_parser() -> BaseLLMParser:
    """Return Ollama parser singleton."""
    global _parser_instance
    if _parser_instance is not None:
        return _parser_instance

    _parser_instance = OllamaLLMParser.get_instance()
    logger.info("Using Ollama API parser")
    return _parser_instance
