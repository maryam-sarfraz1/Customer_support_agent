"""Application service container, built once at startup."""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.graph import build_support_graph
from app.agents.nodes import SupportNodes
from app.agents.workflow import SupportWorkflow
from app.core.config import Settings
from app.db.session import get_session_factory
from app.services.analytics import AnalyticsService
from app.services.email import EmailService
from app.services.feedback import FeedbackService
from app.services.llm import build_chat_model, build_embeddings
from app.services.memory import ConversationMemory
from app.services.messaging import SlackService, WhatsAppService
from app.services.rag import RAGService
from app.services.tickets import TicketService
from app.services.vectorstore import VectorStoreService, build_vector_store


@dataclass
class Container:
    settings: Settings
    rag: RAGService
    memory: ConversationMemory
    tickets: TicketService
    feedback: FeedbackService
    analytics: AnalyticsService
    email: EmailService
    slack: SlackService
    whatsapp: WhatsAppService
    workflow: SupportWorkflow


def build_container(settings: Settings) -> Container:
    session_factory = get_session_factory()

    llm = build_chat_model(settings)
    fast_llm = (
        build_chat_model(settings, model_override=settings.llm_fast_model)
        if settings.llm_fast_model
        else None
    )
    embeddings = build_embeddings(settings)
    store = VectorStoreService(build_vector_store(settings, embeddings))
    rag = RAGService(settings, store)
    memory = ConversationMemory(session_factory)
    tickets = TicketService(session_factory)
    feedback = FeedbackService(session_factory)
    analytics = AnalyticsService(session_factory)
    email = EmailService(settings)
    slack = SlackService(settings)
    whatsapp = WhatsAppService(settings)

    nodes = SupportNodes(settings, llm, rag, tickets, email, slack, fast_llm=fast_llm)
    graph = build_support_graph(settings, nodes)
    workflow = SupportWorkflow(graph, memory)

    return Container(
        settings=settings,
        rag=rag,
        memory=memory,
        tickets=tickets,
        feedback=feedback,
        analytics=analytics,
        email=email,
        slack=slack,
        whatsapp=whatsapp,
        workflow=workflow,
    )
