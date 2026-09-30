"""Manual smoke test: run the vision and text agents on real user-supplied inputs.

Usage:
    python scripts/test_agents.py --image path/to/photo.jpg --text "some report text"

Either flag can be omitted to test only one agent.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def run_vision(image_path: str) -> None:
    from adis.perception.vision.model import VisionDamageAgent

    print(f"\n[vision] loading CLIP model and classifying: {image_path}")
    agent = VisionDamageAgent()
    result = agent.infer(image_path=image_path, location_id="manual-test", source="satellite")
    print(f"[vision] damage_level={result.damage_level.value} "
          f"flood_level={result.flood_level.value} confidence={result.confidence}")


def run_text(text: str) -> None:
    from adis.perception.text.model import TextTriageAgent

    print(f"\n[text] loading NLI model and classifying: {text!r}")
    agent = TextTriageAgent()
    result = agent.infer(text=text, location_id="manual-test", source="social-media")
    print(f"[text] category={result.category.value} severity={result.severity} "
          f"confidence={result.confidence}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", help="Path to an image file to classify")
    parser.add_argument("--text", help="Raw text (social media post / call transcript) to classify")
    args = parser.parse_args()

    if not args.image and not args.text:
        parser.error("Provide at least one of --image or --text")

    if args.image:
        run_vision(args.image)
    if args.text:
        run_text(args.text)
