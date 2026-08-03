"""Deterministic scripted chat model for tests and offline development.

Inspects the incoming prompt and returns plausible structured output for
each agent node so the full LangGraph workflow can run without any API key.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class ScriptedSupportLLM(BaseChatModel):
    """Rule-based stand-in for a real chat model."""

    @property
    def _llm_type(self) -> str:
        return "scripted-support-llm"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        prompt = "\n".join(str(m.content) for m in messages)
        text = self._respond(prompt)
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=text))]
        )

    def _respond(self, prompt: str) -> str:
        lower = prompt.lower()
        if "query understanding agent" in lower:
            # Only inspect the customer's actual message, not the prompt template.
            message = lower.rsplit("customer message:", 1)[-1]
            wants_human = any(
                kw in message
                for kw in ("human", "real person", "speak to someone", "talk to an agent")
            )
            is_complaint = any(
                kw in message
                for kw in ("refund", "broken", "angry", "complaint", "not working")
            )
            intent = (
                "request_human"
                if wants_human
                else "complaint"
                if is_complaint
                else "question"
            )
            user_query = message.strip()[:300]
            return json.dumps(
                {
                    "intent": intent,
                    "language": "en",
                    "rewritten_query": user_query or "customer question",
                    "sentiment": "negative" if is_complaint else "neutral",
                    "category": "billing" if "refund" in message else "general",
                }
            )
        if "verification agent" in lower or "critic" in lower:
            grounded = "context passage" in lower or "[1]" in lower
            return json.dumps(
                {
                    "confidence": 0.9 if grounded else 0.2,
                    "grounded": grounded,
                    "issues": [] if grounded else ["Answer is not supported by sources."],
                }
            )
        if "email agent" in lower:
            return (
                "Subject: Follow-up on your support request\n\n"
                "Hello,\n\nThank you for contacting support. We have logged your "
                "request and our team will follow up shortly.\n\nBest regards,\n"
                "Customer Support Team"
            )
        # Response generation: cite the first context chunk if present.
        if "context passage" in lower:
            return (
                "Based on our documentation, here is the answer to your question. [1]"
            )
        return "Hello! How can I help you with our products today?"
