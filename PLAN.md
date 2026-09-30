# ADIS Project Plan

Goal: take ADIS from concept to (1) a working end-to-end prototype, (2) a publishable
cross-modal fusion architecture, and (3) a patent-eligible verification/dispatch method.

Default assumptions used for this plan (revisit if wrong):
- Solo or small team (2-3 people), starting on local machine + free/low-cost cloud GPU
  (Colab/Kaggle/university lab) rather than a large compute grant.
- Academic/research project timeline (months, not days), targeting a working demo first,
  paper + patent draft as later milestones.
- Python end-to-end. PyTorch for DL, PyTorch Geometric for the GNN, FastAPI for serving.

Adjust phase durations to your real timeline — the **order and dependencies** matter
more than the exact week numbers.

---

## Phase 0 — Foundations (this session)
**Status: done.** Repo scaffold created:
- `src/adis/perception/{vision,text}` — mock perception agents with real-model hooks
- `src/adis/fusion` — rule-based cross-modal verifier (contradiction resolution)
- `src/adis/knowledge_graph` — networkx-based live KG builder + schema
- `src/adis/routing` — Dijkstra damage-aware routing baseline
- `src/adis/orchestrator` — function-pipeline that ties all stages into an `ActionPlan`
- `src/adis/api` — FastAPI `/analyze` endpoint
- `tests/` — offline end-to-end smoke tests (no GPU/datasets required)

**Exit criteria:** `pytest -v` passes; `uvicorn adis.api.main:app` serves a scenario and
returns a prioritized action plan. This is your safety net — every later phase should
keep this test suite green.

## Phase 1 — Perception agents (real models)
1. **Dataset acquisition** (see `docs/datasets.md`): xBD (xView2), FloodNet, CrisisNLP,
   plus start scoping/curating the Andhra Pradesh regional dataset (imagery + local-language
   social text) early — it has the longest lead time (collection/annotation/licensing).
2. **Vision agent**: fine-tune a ViT (or reproduce a DAHiTra-style siamese/transformer
   damage classifier) on xBD for building damage (4 classes) and on FloodNet for flood
   segmentation. Start from a pretrained backbone (timm `vit_base_patch16_224` or a
   Segformer/SegFormer-B0 for segmentation) rather than training from scratch.
   - Baseline metric: F1 per damage class on xBD holdout tier3/test, mIoU on FloodNet test.
   - Handle **unpaired/partial imagery** explicitly (project's stated gap vs DAHiTra) —
     design the model to accept single (post-only) images, not just pre/post pairs.
3. **Text triage agent**: start with a CrisisNLP-labeled classifier (LoRA-fine-tuned small
   LLM, e.g. a 1-3B instruct model, or a lighter DistilBERT/RoBERTa classifier for speed),
   then compare against prompting a larger LLM zero/few-shot. Track latency — golden-window
   use case needs low-latency inference, not just accuracy.
4. Wire real checkpoints into `VisionDamageAgent`/`TextTriageAgent` (`mode: model` in
   `configs/vision.yaml` / `configs/text.yaml`), replacing the `NotImplementedError` stubs.
5. **Exit criteria:** both agents beat a naive baseline (majority class) by a meaningful
   margin on held-out public benchmark splits; inference runs in near-real-time per item.

## Phase 2 — Cross-modal verification agent
1. Build a small labeled set of **agreement/contradiction** cases (vision says road clear,
   text says blocked, and vice versa) — synthesize some from xBD+CrisisNLP location overlaps,
   and hand-label some from the AP regional data.
2. Upgrade `CrossModalVerifier` from the confidence-weighted rule baseline to a learned
   agent: e.g. a small classifier/LLM-judge over `(vision_evidence, text_evidence)` pairs
   that outputs `{agree, vision_wins, text_wins, insufficient_evidence}` + a confidence score.
   Keep the existing rule-based version as a fallback/ablation baseline.
3. This module is your strongest **novelty + patent candidate** — keep a running design log
   (`docs/verification_design_log.md`) of what you tried, why, and what worked, since that
   becomes the basis of both the paper's method section and the patent disclosure.
4. **Exit criteria:** learned verifier measurably outperforms the rule baseline on your
   contradiction test set (precision/recall on correctly resolved contradictions).

## Phase 3 — Knowledge graph + GNN routing
1. Ingest real road networks (OpenStreetMap via `osmnx`) for at least one target region
   (start with an AP flood-prone district) plus hospitals/shelters (OSM tags or manual
   curation). Populate `KnowledgeGraphBuilder` from this real data instead of test fixtures.
2. Replace the Dijkstra baseline in `EvacuationRouter` with a GNN (GraphSAGE/GAT via
   PyTorch Geometric) that predicts **edge traversal cost / node risk** from graph structure
   + verified evidence embeddings, so routing adapts to partial/uncertain damage info, not
   just binary blocked/clear.
   - Keep Dijkstra as the always-available fallback and as an ablation baseline in the paper.
3. Add **rescue-resource allocation**: extend routing to a multi-source multi-sink
   assignment (e.g. min-cost flow or GNN-based allocation) over available rescue units vs.
   ranked-priority locations, not just single shortest paths.
4. **Exit criteria:** GNN routing beats Dijkstra baseline on a held-out synthetic-damage
   test set (e.g. route validity %, average time-to-reach for high-priority nodes).

## Phase 4 — Multi-agent orchestrator (agentic upgrade)
1. Replace the function-pipeline in `orchestrator/pipeline.py` with a real multi-agent
   graph (LangGraph, or a custom state-machine) where perception, verification, KG-update,
   and routing are independent agents that can re-plan, request more evidence, or escalate
   low-confidence cases instead of running once through a fixed chain.
2. Directly address the DORA/DisasterBench-documented failure mode (LLM agents failing at
   reliable multi-step tool orchestration): add explicit tool-call validation, retries, and
   a final consistency check before emitting the action plan.
3. Generate a genuinely **human-readable** action plan (natural-language summary + ranked
   list), not just structured JSON — this is what a responder actually reads.
4. **Exit criteria:** orchestrator handles at least one injected failure case per stage
   (e.g. vision agent times out, text agent returns low confidence, no safe route exists)
   without crashing and with a sensible degraded-but-safe output.

## Phase 5 — Evaluation
1. Benchmark each component against its named baseline from the abstract:
   - Vision: vs. DAHiTra / ViT-on-xBD published numbers.
   - Text: vs. CrisisSense-LLM-style classifiers.
   - Routing: vs. plain GNN-evacuation-routing papers (damage-known assumption).
   - Full pipeline: vs. a naive "manual EOC correlation" simulated baseline (time-to-plan).
2. Run on public benchmarks (xBD, FloodNet, CrisisNLP test splits) **and** the AP regional
   dataset — the regional results are the key differentiator vs. all cited prior work
   (non-US typologies, flood-specific text).
3. Adopt/replicate relevant protocols from DORA and DisasterBench for multi-step agent
   orchestration evaluation, since the abs tract explicitly positions ADIS against their
   findings.
4. **Exit criteria:** a results table per component + end-to-end pipeline latency and
   accuracy numbers, ready to drop into a paper.

## Phase 6 — Write-up, IP, deployment polish
1. Draft the paper around the **cross-modal fusion + verification architecture**
   (Phase 2 is the core novel contribution) with Phase 5 results.
2. Draft an invention disclosure for the verification + dispatch-prioritization method
   (talk to your institution's tech transfer office about patent-eligibility/timing —
   public disclosure via a paper can affect patent rights depending on jurisdiction, so
   sequence disclosure and filing carefully).
3. Polish the demo: Docker image / docker-compose for the API + a minimal frontend map view
   showing live KG state and the current action plan.
4. Package the AP regional dataset (with proper licensing/consent handling) if you intend
   to release it alongside the paper.

---

## Immediate next actions (do these first)
1. `pip install -r requirements.txt && pip install -e . && pytest -v` — confirm the Phase 0
   scaffold runs on your machine.
2. Read `docs/datasets.md` and start the xBD/FloodNet/CrisisNLP registration + download
   processes (these often have manual approval delays — start now, work on Phase 1 code
   while waiting).
3. Start scoping the AP regional dataset collection plan in parallel — it's the longest
   lead-time item and the project's key differentiator.
4. Pick your compute plan (Colab Pro / Kaggle / university GPU / cloud credits) before
   Phase 1 fine-tuning, since ViT fine-tuning on xBD is the first GPU-heavy step.

## Risks / things to watch
- **Dataset access delays** (xBD/FloodNet/CrisisNLP registration, AP data collection) —
  the biggest schedule risk; start Phase 1 dataset acquisition immediately.
- **Novelty overlap**: keep explicit ablations vs. DAHiTra/CrisisSense-LLM/GNN-routing so
  the paper's contribution claim (fusion + verification + closed-loop routing) is defensible.
- **Agentic reliability**: DORA/DisasterBench findings suggest multi-step tool orchestration
  is genuinely hard — budget real time for Phase 4 failure-mode testing, not just happy-path.
- **Scope creep**: the abstract is broad (5 data modalities, 3 model families, 2 benchmarks
  + a new dataset). Phase 0-3 already gives you a defensible, demoable system — treat
  Phases 5-6 breadth (more benchmarks, more baselines) as expandable, not blocking.
