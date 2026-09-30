# ADIS — Autonomous Disaster Intelligence System

ADIS is an autonomous, multimodal AI system that fuses satellite/drone imagery, CCTV,
social media, and emergency-call data to produce a live, prioritized action plan for
disaster responders — closing the loop between **perception** (what's damaged),
**verification** (what's actually true), and **routing** (how to reach it safely).

```
 Satellite/Drone/CCTV ─▶ Vision (ViT) damage/flood agent ─┐
                                                            ├─▶ Cross-Modal Verifier ─▶ Knowledge Graph ─▶ GNN Routing ─▶ Orchestrator ─▶ Action Plan
 Social media/Calls   ─▶ Text (LLM) triage agent          ─┘
```

See [PLAN.md](PLAN.md) for the full phased roadmap and [docs/architecture.md](docs/architecture.md)
for the detailed system diagram.

## Repo layout

```
src/adis/
  perception/vision/   ViT-based damage + flood segmentation agent
  perception/text/     LLM-based social media / call triage agent
  fusion/               Cross-modal verification agent (contradiction resolution)
  knowledge_graph/      Live graph of roads, buildings, hospitals, shelters (networkx)
  routing/              Damage-aware evacuation routing (Dijkstra baseline → GNN)
  orchestrator/         Ties every agent together into a prioritized action plan
  api/                  FastAPI service exposing POST /analyze
configs/                 YAML configs per component
docs/                    Architecture, dataset acquisition, evaluation protocol
scripts/                 Dataset download / environment setup helpers
tests/                   Pytest suite (runs fully offline in "mock" mode)
```

## Current status

Phase 0 scaffold: every stage of the pipeline is wired end-to-end and runnable
**without any GPU, model weights, or datasets**, using deterministic "mock" perception
agents and a Dijkstra routing baseline. This lets you validate the full architecture,
data contracts, and orchestration logic immediately, then swap in real trained models
component-by-component per [PLAN.md](PLAN.md) without changing the pipeline shape.

## Quickstart

```bash
# 1. Create environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

# 2. Run the offline test suite (mock perception agents, no downloads needed)
pytest -v

# 3. Run the API locally
uvicorn adis.api.main:app --reload
# then POST a scenario to http://127.0.0.1:8000/analyze (see docs/architecture.md for payload shape)
```

To enable real models later (Phase 1+): `pip install -r requirements-ml.txt` and set
`mode: model` in the relevant `configs/*.yaml`.

## License / provenance note

This project targets a patent-eligible verification/dispatch-prioritization method
(see PLAN.md Phase 6) — keep implementation notes and novel design decisions logged in
`docs/` as they're made, for later IP disclosure drafting.
