"""LLM and embedding model factories (OpenAI / Gemini / Ollama / fake).

Provider SDKs are imported lazily so that only the configured provider's
package needs to be installed.
"""

from __future__ import annotations

import logging

from langchain_core.embeddings import DeterministicFakeEmbedding, Embeddings
from langchain_core.language_models import BaseChatModel

from app.core.config import Settings
from app.core.exceptions import LLMError

logger = logging.getLogger(__name__)


def build_chat_model(
    settings: Settings, model_override: str | None = None
) -> BaseChatModel:
    provider = settings.llm_provider
    if model_override:
        settings = settings.model_copy(update={"llm_model": model_override})
    try:
        if provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                api_key=settings.openai_api_key or None,
                timeout=60,
                max_retries=2,
            )
        if provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                google_api_key=settings.google_api_key or None,
                timeout=60,
                max_retries=2,
            )
        if provider == "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                base_url=settings.ollama_base_url,
            )
        if provider == "fake":
            from app.services.fake_llm import ScriptedSupportLLM

            return ScriptedSupportLLM()
    except ImportError as exc:
        raise LLMError(
            f"LLM provider '{provider}' selected but its package is not installed: {exc}"
        ) from exc
    raise LLMError(f"Unknown LLM provider: {provider}")


def build_embeddings(settings: Settings) -> Embeddings:
    provider = settings.embedding_provider
    try:
        if provider == "openai":
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(
                model=settings.embedding_model,
                api_key=settings.openai_api_key or None,
            )
        if provider == "gemini":
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            return GoogleGenerativeAIEmbeddings(
                model=settings.embedding_model,
                google_api_key=settings.google_api_key or None,
            )
        if provider == "ollama":
            from langchain_ollama import OllamaEmbeddings

            return OllamaEmbeddings(
                model=settings.embedding_model,
                base_url=settings.ollama_base_url,
            )
        if provider == "fake":
            return DeterministicFakeEmbedding(size=384)
    except ImportError as exc:
        raise LLMError(
            f"Embedding provider '{provider}' selected but its package is not "
            f"installed: {exc}"
        ) from exc
    raise LLMError(f"Unknown embedding provider: {provider}")
