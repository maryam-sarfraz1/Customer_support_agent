"""LangGraph node implementations for the support workflow.

Each node is an async method on `SupportNodes`, which carries the service
dependencies (LLM, RAG, tickets, email, Slack). Nodes return partial state
updates per the LangGraph convention.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from app.agents import prompts
from app.agents.state import RetrievedChunk, SupportState
from app.core.config import Settings
from app.schemas.tickets import TicketCreate
from app.services.email import EmailService
from app.services.messaging import SlackService
from app.services.rag import RAGService
from app.services.tickets import TicketService

logger = logging.getLogger(__name__)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_json(text: str) -> dict[str, Any]:
    """Extract the first JSON object from an LLM response; {} on failure."""
    match = _JSON_RE.search(text)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _format_history(history: list[dict[str, str]]) -> str:
    if not history:
        return "(no prior messages)"
    return "\n".join(f"{m['role']}: {m['content'][:500]}" for m in history[-10:])


def _format_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(no relevant context found)"
    return "\n\n".join(
        f"Context passage [{i + 1}] (source: {c['title']}, type: {c['source_type']}):\n"
        f"{c['content']}"
        for i, c in enumerate(chunks)
    )


class SupportNodes:
    def __init__(
        self,
        settings: Settings,
        llm: BaseChatModel,
        rag: RAGService,
        tickets: TicketService,
        email: EmailService,
        slack: SlackService,
        fast_llm: BaseChatModel | None = None,
    ) -> None:
        self._settings = settings
        self._llm = llm
        # Smaller/faster model for classification-style steps; the main
        # model still writes every customer-facing answer.
        self._fast_llm = fast_llm or llm
        self._rag = rag
        self._tickets = tickets
        self._email = email
        self._slack = slack

    async def _invoke(self, prompt: str, *, fast: bool = False) -> str:
        model = self._fast_llm if fast else self._llm
        try:
            response = await model.ainvoke([HumanMessage(content=prompt)])
        except Exception:
            backup = self._llm if fast else self._fast_llm
            if backup is model:
                raise
            # Provider overload (e.g. 503 on one model) — try the other tier.
            logger.warning("Primary model call failed; retrying with backup model")
            response = await backup.ainvoke([HumanMessage(content=prompt)])
        content = response.content
        if isinstance(content, list):  # some providers return content blocks
            content = "".join(
                block if isinstance(block, str) else block.get("text", "")
                for block in content
            )
        return str(content)

    # ------------------------------------------------------------------ nodes

    async def understand(self, state: SupportState) -> dict[str, Any]:
        """Query Understanding Agent: intent, language, rewritten query."""
        prompt = prompts.QUERY_UNDERSTANDING_PROMPT.format(
            history=_format_history(state.get("history", [])),
            message=state["message"],
        )
        try:
            parsed = _parse_json(await self._invoke(prompt, fast=True))
        except Exception:
            logger.exception("Query understanding failed; using fallbacks")
            parsed = {}
        intent = parsed.get("intent", "question")
        if intent not in ("question", "complaint", "request_human", "chitchat"):
            intent = "question"
        return {
            "intent": intent,
            "language": state.get("forced_language")
            or parsed.get("language", "en"),
            "rewritten_query": parsed.get("rewritten_query") or state["message"],
            "sentiment": parsed.get("sentiment", "neutral"),
            "category": parsed.get("category", "general"),
        }

    async def retrieve(self, state: SupportState) -> dict[str, Any]:
        """Retrieval Agent: fetch relevant KB chunks."""
        query = state.get("rewritten_query") or state["message"]
        attempts = state.get("retrieval_attempts", 0) + 1
        # On a retry after a failed verification, widen the search.
        top_k = self._settings.retrieval_top_k * attempts
        try:
            results = await self._rag.retrieve(query, top_k=top_k)
        except Exception:
            logger.exception("Retrieval failed")
            results = []
        chunks: list[RetrievedChunk] = [
            {
                "content": doc.page_content,
                "title": str(doc.metadata.get("title", "Unknown")),
                "source_type": str(doc.metadata.get("source_type", "documentation")),
                "source_url": str(doc.metadata.get("source_url", "")),
                "score": float(score),
            }
            for doc, score in results
        ]
        return {"retrieved": chunks, "retrieval_attempts": attempts}

    async def generate(self, state: SupportState) -> dict[str, Any]:
        """Response Generation Agent: grounded, cited answer."""
        chunks = state.get("retrieved", [])
        prompt = prompts.GENERATION_PROMPT.format(
            language=state.get("language", "en"),
            context=_format_context(chunks),
            history=_format_history(state.get("history", [])),
            question=state["message"],
        )
        try:
            answer = await self._invoke(prompt)
        except Exception:
            logger.exception("Generation failed")
            return {
                "answer": "",
                "citations": [],
                "needs_escalation": True,
                "escalation_reason": "llm_error",
            }
        cited_indices = {
            int(m) for m in re.findall(r"\[(\d+)\]", answer)
        }
        citations = [
            {
                "index": i + 1,
                "source": c["title"],
                "snippet": c["content"][:300],
                "score": c["score"],
            }
            for i, c in enumerate(chunks)
            if (i + 1) in cited_indices
        ]
        return {"answer": answer, "citations": citations}

    async def chitchat(self, state: SupportState) -> dict[str, Any]:
        """Handle conversational messages without retrieval."""
        prompt = prompts.CHITCHAT_PROMPT.format(
            language=state.get("language", "en"),
            history=_format_history(state.get("history", [])),
            message=state["message"],
        )
        try:
            answer = await self._invoke(prompt)
        except Exception:
            logger.exception("Chitchat generation failed")
            answer = "Hello! How can I help you today?"
        return {"answer": answer, "citations": [], "confidence": 1.0, "grounded": True}

    async def verify(self, state: SupportState) -> dict[str, Any]:
        """Verification/Critic Agent: grade groundedness and confidence."""
        chunks = state.get("retrieved", [])
        prompt = prompts.CRITIC_PROMPT.format(
            question=state["message"],
            context=_format_context(chunks),
            answer=state.get("answer", ""),
        )
        try:
            parsed = _parse_json(await self._invoke(prompt, fast=True))
        except Exception:
            logger.exception("Verification failed; falling back to retrieval scores")
            parsed = {}
        if parsed:
            confidence = float(parsed.get("confidence", 0.0))
            grounded = bool(parsed.get("grounded", False))
            issues = [str(i) for i in parsed.get("issues", [])]
        else:
            # Heuristic fallback: trust the best retrieval score.
            best = max((c["score"] for c in chunks), default=0.0)
            confidence, grounded, issues = best, best >= 0.5, ["critic_unavailable"]
        confidence = max(0.0, min(1.0, confidence))
        return {"confidence": confidence, "grounded": grounded, "critic_issues": issues}

    async def escalate(self, state: SupportState) -> dict[str, Any]:
        """Human Escalation Agent: flag handoff and notify the support team."""
        reason = state.get("escalation_reason") or (
            "customer_requested_human"
            if state.get("intent") == "request_human"
            else "low_confidence"
        )
        summary = (
            f"Escalation ({reason}) — conversation {state.get('conversation_id')}\n"
            f"Customer: {state.get('customer_email') or 'unknown'}\n"
            f"Message: {state['message'][:500]}\n"
            f"Confidence: {state.get('confidence', 0.0):.2f}"
        )
        try:
            await self._slack.notify(f":rotating_light: {summary}")
        except Exception:
            logger.exception("Slack escalation notification failed")
        handoff_message = state.get("answer") or ""
        if not handoff_message or reason != "low_confidence":
            handoff_message = (
                "I've forwarded your request to a human support agent who will "
                "get back to you shortly."
            )
        else:
            handoff_message += (
                "\n\nI'm not fully certain about this answer, so I've also looped "
                "in a human agent to confirm."
            )
        return {
            "needs_escalation": True,
            "escalation_reason": reason,
            "answer": handoff_message,
        }

    async def create_ticket(self, state: SupportState) -> dict[str, Any]:
        """Ticket Management Agent: open a ticket for escalations/complaints."""
        priority = (
            "high" if state.get("sentiment") == "negative" else "medium"
        )
        try:
            ticket = await self._tickets.create(
                TicketCreate(
                    subject=state["message"][:200],
                    description=(
                        f"Intent: {state.get('intent')}\n"
                        f"Reason: {state.get('escalation_reason', 'n/a')}\n"
                        f"Confidence: {state.get('confidence', 0.0):.2f}\n\n"
                        f"Customer message:\n{state['message']}\n\n"
                        f"Draft answer:\n{state.get('answer', '(none)')}"
                    ),
                    priority=priority,
                    category=state.get("category", "general"),
                    customer_email=state.get("customer_email", ""),
                    conversation_id=state.get("conversation_id"),
                )
            )
        except Exception:
            logger.exception("Ticket creation failed")
            return {"ticket_id": None}
        return {"ticket_id": ticket.id}

    async def draft_email(self, state: SupportState) -> dict[str, Any]:
        """Email Agent: draft (and optionally send) a follow-up email."""
        ticket_id = state.get("ticket_id")
        if not ticket_id:
            return {"email_draft": None}
        prompt = prompts.EMAIL_PROMPT.format(
            language=state.get("language", "en"),
            ticket_id=ticket_id,
            summary=state["message"][:800],
            status="escalated to a human agent"
            if state.get("needs_escalation")
            else "resolved by the assistant",
        )
        try:
            draft = await self._invoke(prompt)
        except Exception:
            logger.exception("Email drafting failed")
            return {"email_draft": None}
        to = state.get("customer_email", "")
        if to and self._email.enabled:
            subject = "Your support request"
            body = draft
            if draft.lower().startswith("subject:"):
                first_line, _, rest = draft.partition("\n")
                subject = first_line.split(":", 1)[1].strip() or subject
                body = rest.strip()
            try:
                await self._email.send(to, subject, body)
            except Exception:
                logger.exception("Email send failed")
        return {"email_draft": draft}
