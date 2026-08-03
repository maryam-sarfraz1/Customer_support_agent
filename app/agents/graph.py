"""LangGraph workflow assembly.

Flow:

    START -> understand
      understand -> chitchat            (conversational message)
      understand -> escalate            (customer asks for a human)
      understand -> retrieve            (question / complaint)
    retrieve -> generate -> verify
      verify -> retrieve                (low confidence, first attempt: widen search)
      verify -> escalate                (still low confidence after retry)
      verify -> ticket                  (complaint: always open a ticket)
      verify -> END                     (confident answer)
    escalate -> ticket -> email -> END
    chitchat -> END
"""

from __future__ import annotations

import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import SupportNodes
from app.agents.state import SupportState
from app.core.config import Settings

logger = logging.getLogger(__name__)

MAX_RETRIEVAL_ATTEMPTS = 2


def build_support_graph(settings: Settings, nodes: SupportNodes):
    """Compile the multi-agent support workflow."""

    def route_after_understand(
        state: SupportState,
    ) -> Literal["chitchat", "escalate", "retrieve"]:
        intent = state.get("intent", "question")
        if intent == "chitchat":
            return "chitchat"
        if intent == "request_human":
            return "escalate"
        return "retrieve"

    def route_after_verify(
        state: SupportState,
    ) -> Literal["retrieve", "escalate", "ticket", "__end__"]:
        confidence = state.get("confidence", 0.0)
        threshold = settings.confidence_threshold
        if confidence < threshold:
            if state.get("retrieval_attempts", 0) < MAX_RETRIEVAL_ATTEMPTS:
                logger.info(
                    "Low confidence %.2f; retrying retrieval with wider search",
                    confidence,
                )
                return "retrieve"
            return "escalate"
        if state.get("intent") == "complaint":
            return "ticket"
        return "__end__"

    graph = StateGraph(SupportState)
    graph.add_node("understand", nodes.understand)
    graph.add_node("retrieve", nodes.retrieve)
    graph.add_node("generate", nodes.generate)
    graph.add_node("verify", nodes.verify)
    graph.add_node("chitchat", nodes.chitchat)
    graph.add_node("escalate", nodes.escalate)
    graph.add_node("ticket", nodes.create_ticket)
    graph.add_node("email", nodes.draft_email)

    graph.add_edge(START, "understand")
    graph.add_conditional_edges(
        "understand",
        route_after_understand,
        {"chitchat": "chitchat", "escalate": "escalate", "retrieve": "retrieve"},
    )
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "verify")
    graph.add_conditional_edges(
        "verify",
        route_after_verify,
        {
            "retrieve": "retrieve",
            "escalate": "escalate",
            "ticket": "ticket",
            "__end__": END,
        },
    )
    graph.add_edge("chitchat", END)
    graph.add_edge("escalate", "ticket")
    graph.add_edge("ticket", "email")
    graph.add_edge("email", END)

    return graph.compile()
