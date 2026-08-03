"""Cross-modal verification agent.

Fuses vision-based DamageAssessment and text-based TriageReport evidence for
the same location, scores overall confidence, and resolves contradictions
(e.g. imagery shows a clear road while social media reports it blocked).

This is the Phase 0/1 rule-based baseline. Phase 2 (see PLAN.md) upgrades
this to a learned verification agent trained on labeled agreement/
contradiction cases; keep this rule-based version as an ablation baseline.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from adis.perception.text.model import TriageCategory, TriageReport
from adis.perception.vision.model import DamageAssessment, DamageLevel, FloodLevel


@dataclass
class VerifiedEvidence:
    location_id: str
    road_status: str  # "clear" | "blocked" | "unknown"
    damage_level: DamageLevel | None
    flood_level: FloodLevel | None
    casualty_reported: bool
    confidence: float
    contradiction: bool
    notes: list[str] = field(default_factory=list)


class CrossModalVerifier:
    """Resolves agreement/contradiction between visual and textual evidence.

    Baseline strategy (rule-based, Phase 0/1):
    - Weight each modality by its own confidence.
    - Flag a contradiction when vision and text disagree on road passability.
    - Resolve by preferring the higher-confidence modality; if confidences are
      too close to call, default to the safer ("blocked") assumption.
    """

    CONTRADICTION_MARGIN = 0.15

    def verify(
        self,
        location_id: str,
        vision_evidence: list[DamageAssessment],
        text_evidence: list[TriageReport],
    ) -> VerifiedEvidence:
        notes: list[str] = []

        vision_road_clear = self._vision_says_road_clear(vision_evidence)
        text_road_clear = self._text_says_road_clear(text_evidence)

        contradiction = False
        road_status = "unknown"
        if vision_road_clear is not None and text_road_clear is not None:
            if vision_road_clear != text_road_clear:
                contradiction = True
                notes.append(
                    "Vision/text disagreement on road passability; "
                    "resolved via confidence-weighted vote."
                )
                road_status = self._resolve_contradiction(vision_evidence, text_evidence)
            else:
                road_status = "clear" if vision_road_clear else "blocked"
        elif vision_road_clear is not None:
            road_status = "clear" if vision_road_clear else "blocked"
        elif text_road_clear is not None:
            road_status = "clear" if text_road_clear else "blocked"

        casualty_reported = any(t.category == TriageCategory.CASUALTY for t in text_evidence)
        damage_level = self._worst_damage(vision_evidence)
        flood_level = self._worst_flood(vision_evidence)
        confidence = self._aggregate_confidence(vision_evidence, text_evidence, contradiction)

        return VerifiedEvidence(
            location_id=location_id,
            road_status=road_status,
            damage_level=damage_level,
            flood_level=flood_level,
            casualty_reported=casualty_reported,
            confidence=round(confidence, 2),
            contradiction=contradiction,
            notes=notes,
        )

    @staticmethod
    def _vision_says_road_clear(vision_evidence: list[DamageAssessment]) -> bool | None:
        if not vision_evidence:
            return None
        order = list(DamageLevel)
        worst = max(vision_evidence, key=lambda v: order.index(v.damage_level))
        return worst.damage_level in (DamageLevel.NO_DAMAGE, DamageLevel.MINOR_DAMAGE)

    @staticmethod
    def _text_says_road_clear(text_evidence: list[TriageReport]) -> bool | None:
        relevant = [
            t for t in text_evidence if t.category in (TriageCategory.ROAD_BLOCKED, TriageCategory.ROAD_CLEAR)
        ]
        if not relevant:
            return None
        blocked_conf = sum(t.confidence for t in relevant if t.category == TriageCategory.ROAD_BLOCKED)
        clear_conf = sum(t.confidence for t in relevant if t.category == TriageCategory.ROAD_CLEAR)
        return clear_conf >= blocked_conf

    def _resolve_contradiction(
        self, vision_evidence: list[DamageAssessment], text_evidence: list[TriageReport]
    ) -> str:
        vision_conf = max((v.confidence for v in vision_evidence), default=0.0)
        text_conf = max((t.confidence for t in text_evidence), default=0.0)
        if vision_conf >= text_conf + self.CONTRADICTION_MARGIN:
            clear = self._vision_says_road_clear(vision_evidence)
        elif text_conf >= vision_conf + self.CONTRADICTION_MARGIN:
            clear = self._text_says_road_clear(text_evidence)
        else:
            clear = False  # too close to call: default to the safer assumption
        return "clear" if clear else "blocked"

    @staticmethod
    def _worst_damage(vision_evidence: list[DamageAssessment]) -> DamageLevel | None:
        if not vision_evidence:
            return None
        order = list(DamageLevel)
        return max((v.damage_level for v in vision_evidence), key=order.index)

    @staticmethod
    def _worst_flood(vision_evidence: list[DamageAssessment]) -> FloodLevel | None:
        if not vision_evidence:
            return None
        order = list(FloodLevel)
        return max((v.flood_level for v in vision_evidence), key=order.index)

    @staticmethod
    def _aggregate_confidence(
        vision_evidence: list[DamageAssessment],
        text_evidence: list[TriageReport],
        contradiction: bool,
    ) -> float:
        confidences = [v.confidence for v in vision_evidence] + [t.confidence for t in text_evidence]
        if not confidences:
            return 0.0
        avg = sum(confidences) / len(confidences)
        return avg * (0.7 if contradiction else 1.0)
