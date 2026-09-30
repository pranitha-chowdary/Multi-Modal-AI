"""Vision agent service wrapper.

Thin async service layer around `adis.perception.vision.model.VisionDamageAgent`
so the orchestrator/API can call it alongside other agents without blocking
the event loop. Holds no model logic itself - the real CLIP-backed inference
lives in `VisionDamageAgent`; swap that agent's checkpoint (see PLAN.md Phase 1)
without touching this service layer.
"""
from __future__ import annotations

import asyncio

from adis.perception.vision.model import DamageAssessment, VisionDamageAgent


class VisionAgentService:
    def __init__(self, agent: VisionDamageAgent | None = None):
        self.agent = agent or VisionDamageAgent()

    async def run(self, image_path: str, location_id: str, source: str = "satellite") -> DamageAssessment:
        # CLIP inference is CPU/GPU-bound and synchronous; run off the event loop.
        return await asyncio.to_thread(self.agent.infer, image_path, location_id, source)
