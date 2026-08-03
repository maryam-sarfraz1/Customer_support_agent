"""High-level entry point that runs the LangGraph workflow for one turn."""

from __future__ import annotations

import logging
import time

from app.agents.state import SupportState
from app.schemas.chat import ChatRequest, ChatResponse, Citation
from app.services.memory import ConversationMemory

logger = logging.getLogger(__name__)


class SupportWorkflow:
    def __init__(self, graph, memory: ConversationMemory) -> None:
        self._graph = graph
        self._memory = memory

    async def run(self, request: ChatRequest, user_id: str | None = None) -> ChatResponse:
        started = time.monotonic()
        conversation = await self._memory.get_or_create_conversation(
            request.conversation_id, channel=request.channel, user_id=user_id
        )
        history = await self._memory.history(conversation.id)
        await self._memory.append_user_message(conversation.id, request.message)

        initial: SupportState = {
            "conversation_id": conversation.id,
            "message": request.message,
            "channel": request.channel,
            "customer_email": request.customer_email,
            "forced_language": request.language,
            "history": history,
        }
        final: SupportState = await self._graph.ainvoke(initial)

        latency_ms = int((time.monotonic() - started) * 1000)
        answer = final.get("answer") or (
            "I'm sorry, something went wrong while handling your request. "
            "A human agent will follow up with you."
        )
        citations = final.get("citations", []) or []
        assistant_msg = await self._memory.append_assistant_message(
            conversation.id,
            answer,
            intent=final.get("intent"),
            confidence=final.get("confidence"),
            escalated=bool(final.get("needs_escalation")),
            citations=citations,
            latency_ms=latency_ms,
        )
        return ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant_msg.id,
            answer=answer,
            citations=[Citation(**c) for c in citations],
            confidence=float(final.get("confidence", 0.0)),
            intent=final.get("intent", "question"),
            language=final.get("language", "en"),
            escalated=bool(final.get("needs_escalation")),
            ticket_id=final.get("ticket_id"),
            email_draft=final.get("email_draft"),
            latency_ms=latency_ms,
        )
