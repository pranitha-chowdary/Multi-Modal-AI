"""Cross-modal verification agent service wrapper.

Thin async service layer around `adis.fusion.verifier.CrossModalVerifier` so
the orchestrator/API can call it alongside the vision/text agents without
blocking the event loop. Holds no verification logic itself - the real
confidence-weighted contradiction resolution lives in `CrossModalVerifier`
(see PLAN.md Phase 2 for the learned-agent upgrade path).
"""
from __future__ import annotations

import asyncio

from adis.fusion.verifier import CrossModalVerifier, VerifiedEvidence
from adis.perception.text.model import TriageReport
from adis.perception.vision.model import DamageAssessment


class VerificationAgentService:
    def __init__(self, agent: CrossModalVerifier | None = None):
        self.agent = agent or CrossModalVerifier()

    async def run(
        self,
        location_id: str,
        vision_evidence: list[DamageAssessment],
        text_evidence: list[TriageReport],
    ) -> VerifiedEvidence:
        return await asyncio.to_thread(self.agent.verify, location_id, vision_evidence, text_evidence)
