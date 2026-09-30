"""Text triage agent service wrapper.

Thin async service layer around `adis.perception.text.model.TextTriageAgent`
so the orchestrator/API can call it alongside other agents without blocking
the event loop. Holds no model logic itself - the real NLI-backed inference
lives in `TextTriageAgent`; swap that agent's checkpoint (see PLAN.md Phase 1)
without touching this service layer.
"""
from __future__ import annotations

import asyncio

from adis.perception.text.model import TextTriageAgent, TriageReport


class TextAgentService:
    def __init__(self, agent: TextTriageAgent | None = None):
        self.agent = agent or TextTriageAgent()

    async def run(self, text: str, location_id: str, source: str = "social-media") -> TriageReport:
        # NLI zero-shot inference is synchronous; run off the event loop.
        return await asyncio.to_thread(self.agent.infer, text, location_id, source)
