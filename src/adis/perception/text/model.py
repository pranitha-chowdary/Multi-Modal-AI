"""LLM-based text triage agent for social media reports and emergency calls.

Runs real-time zero-shot text classification using a pretrained NLI model
(typeform/distilbert-base-uncased-mnli) - there is no keyword-matching/mocked
path in this module. Every call to `infer` is a genuine forward pass: the
raw text is scored against natural-language hypotheses for each triage
category and the highest-scoring one wins.

Phase 1 (see PLAN.md) fine-tunes/LoRA-adapts a model on CrisisNLP-labeled
data for higher accuracy on this exact task; swap the checkpoint via
`model_name` once that lands.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

from transformers import pipeline as hf_pipeline

_DEFAULT_MODEL_NAME = "typeform/distilbert-base-uncased-mnli"

# Below this confidence, none of the candidate categories are reliable enough
# to act on; fall back to INFO_ONLY rather than asserting an actionable category.
_CONFIDENCE_THRESHOLD = 0.45


class TriageCategory(str, Enum):
    CASUALTY = "casualty"
    ROAD_BLOCKED = "road-blocked"
    ROAD_CLEAR = "road-clear"
    RESCUE_NEEDED = "rescue-needed"
    RESOURCE_REQUEST = "resource-request"
    INFO_ONLY = "info-only"


_CATEGORY_HYPOTHESES: dict[TriageCategory, str] = {
    TriageCategory.CASUALTY: "This message reports a casualty, injury, or death.",
    TriageCategory.ROAD_BLOCKED: "This message reports a road, bridge, or path is blocked or impassable.",
    TriageCategory.ROAD_CLEAR: "This message reports a road or path is clear and passable.",
    TriageCategory.RESCUE_NEEDED: "This message is an urgent request for rescue or help.",
    TriageCategory.RESOURCE_REQUEST: "This message requests food, water, medicine, or other supplies.",
    TriageCategory.INFO_ONLY: "This message is general information with no urgent request.",
}

_SEVERITY_BY_CATEGORY: dict[TriageCategory, float] = {
    TriageCategory.CASUALTY: 1.0,
    TriageCategory.RESCUE_NEEDED: 0.9,
    TriageCategory.ROAD_BLOCKED: 0.6,
    TriageCategory.RESOURCE_REQUEST: 0.5,
    TriageCategory.ROAD_CLEAR: 0.1,
    TriageCategory.INFO_ONLY: 0.1,
}


@dataclass
class TriageReport:
    location_id: str
    source: str  # "social-media" | "emergency-call" | "cctv-caption"
    category: TriageCategory
    severity: float  # 0-1
    confidence: float  # 0-1, real zero-shot classification score of the winning label
    raw_text: str


@lru_cache(maxsize=4)
def _load_zero_shot_pipeline(model_name: str):
    """Download (once, cached on disk by huggingface_hub) and load a real
    zero-shot NLI classification pipeline. Cached in-process via lru_cache so
    repeated agent construction doesn't reload the model.
    """
    return hf_pipeline("zero-shot-classification", model=model_name)


class TextTriageAgent:
    """Real-time zero-shot text triage classifier backed by an NLI model.

    Every call to `infer` runs a genuine forward pass through the model - no
    fallback/placeholder path.
    """

    def __init__(self, model_name: str = _DEFAULT_MODEL_NAME):
        self.model_name = model_name
        self._classifier = _load_zero_shot_pipeline(model_name)
        self._categories = list(_CATEGORY_HYPOTHESES.keys())
        self._hypotheses = [_CATEGORY_HYPOTHESES[c] for c in self._categories]

    def infer(self, text: str, location_id: str, source: str = "social-media") -> TriageReport:
        result = self._classifier(text, candidate_labels=self._hypotheses)
        best_hypothesis = result["labels"][0]
        best_score = result["scores"][0]
        category = self._categories[self._hypotheses.index(best_hypothesis)]
        if best_score < _CONFIDENCE_THRESHOLD:
            category = TriageCategory.INFO_ONLY

        return TriageReport(
            location_id=location_id,
            source=source,
            category=category,
            severity=_SEVERITY_BY_CATEGORY[category],
            confidence=round(float(best_score), 3),
            raw_text=text,
        )
