"""ADIS: Autonomous Disaster Intelligence System."""
import os
from pathlib import Path

# Default the HuggingFace model cache to a writable directory inside the repo.
# Real model downloads (CLIP, NLI zero-shot classifier) need somewhere to
# write; the user's home cache dir may be read-only in sandboxed/CI
# environments, so this must be set before any transformers import happens.
_DEFAULT_HF_CACHE = Path(__file__).resolve().parents[2] / ".cache" / "huggingface"
os.environ.setdefault("HF_HOME", str(_DEFAULT_HF_CACHE))
# The Xet fast-download backend doesn't work through this environment's network
# sandbox; fall back to plain HTTP downloads from the HF Hub.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

__version__ = "0.1.0"
