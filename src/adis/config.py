"""Configuration loading utilities."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs"


def load_config(name: str) -> dict[str, Any]:
    """Load a YAML config file from the configs/ directory by name (no extension).

    Example: load_config("vision") -> configs/vision.yaml contents as a dict.
    """
    path = CONFIG_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}
