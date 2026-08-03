"""Vision damage/flood perception agent.

Runs real-time zero-shot image classification using a pretrained CLIP model
(openai/clip-vit-base-patch32) - there is no synthetic/hashed/mocked output
anywhere in this module. CLIP scores each real input image against
natural-language damage-level and flood-level descriptions and returns the
best-matching label with its genuine softmax confidence from a real forward
pass.

This gives real (if not yet domain-fine-tuned) inference from the moment the
repo is set up, with no training required. Phase 1 (see PLAN.md) fine-tunes a
ViT/segmentation head on xBD + FloodNet for higher accuracy on this exact
task; once that checkpoint exists, load it via `finetuned_checkpoint_path`.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

_CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"


class DamageLevel(str, Enum):
    NO_DAMAGE = "no-damage"
    MINOR_DAMAGE = "minor-damage"
    MAJOR_DAMAGE = "major-damage"
    DESTROYED = "destroyed"


class FloodLevel(str, Enum):
    DRY = "dry"
    PARTIAL = "partial-flood"
    FULL = "full-flood"


_DAMAGE_PROMPTS: dict[DamageLevel, str] = {
    DamageLevel.NO_DAMAGE: "an aerial photo of an undamaged, intact building and street",
    DamageLevel.MINOR_DAMAGE: "an aerial photo of a building with minor structural damage",
    DamageLevel.MAJOR_DAMAGE: "an aerial photo of a building with major structural damage or partial collapse",
    DamageLevel.DESTROYED: "an aerial photo of a completely destroyed, collapsed building or rubble",
}

_FLOOD_PROMPTS: dict[FloodLevel, str] = {
    FloodLevel.DRY: "an aerial photo of a dry area with no flooding",
    FloodLevel.PARTIAL: "an aerial photo of a partially flooded area with some standing water",
    FloodLevel.FULL: "an aerial photo of a fully flooded area completely submerged in water",
}


@dataclass
class DamageAssessment:
    location_id: str
    source: str  # "satellite" | "drone" | "cctv"
    damage_level: DamageLevel
    flood_level: FloodLevel
    confidence: float  # 0-1, real softmax probability of the winning damage label


@lru_cache(maxsize=4)
def _load_clip(model_name: str) -> tuple[CLIPModel, CLIPProcessor]:
    """Download (once, cached on disk by huggingface_hub) and load a real CLIP
    checkpoint. Cached in-process via lru_cache so repeated agent construction
    doesn't reload the model.
    """
    model = CLIPModel.from_pretrained(model_name)
    processor = CLIPProcessor.from_pretrained(model_name)
    model.eval()
    return model, processor


class VisionDamageAgent:
    """Real-time zero-shot damage/flood classifier backed by CLIP.

    Every call to `infer` opens the real image file and performs a genuine
    forward pass through CLIP - no fallback/placeholder path.
    """

    def __init__(self, model_name: str = _CLIP_MODEL_NAME):
        self.model_name = model_name
        self.model, self.processor = _load_clip(model_name)
        self._damage_labels = list(_DAMAGE_PROMPTS.keys())
        self._flood_labels = list(_FLOOD_PROMPTS.keys())
        self._damage_prompts = [_DAMAGE_PROMPTS[k] for k in self._damage_labels]
        self._flood_prompts = [_FLOOD_PROMPTS[k] for k in self._flood_labels]

    def infer(self, image_path: str, location_id: str, source: str = "satellite") -> DamageAssessment:
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        image = Image.open(image_path).convert("RGB")

        damage_level, damage_conf = self._classify(image, self._damage_prompts, self._damage_labels)
        flood_level, _flood_conf = self._classify(image, self._flood_prompts, self._flood_labels)

        return DamageAssessment(location_id, source, damage_level, flood_level, round(damage_conf, 3))

    def _classify(self, image: Image.Image, prompts: list[str], labels: list) -> tuple:
        inputs = self.processor(text=prompts, images=image, return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = outputs.logits_per_image.softmax(dim=1)[0]
        best_idx = int(torch.argmax(probs).item())
        return labels[best_idx], float(probs[best_idx].item())
