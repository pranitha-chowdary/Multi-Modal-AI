# Evaluation protocol

## Per-component benchmarks

| Component | Dataset(s) | Metric(s) | Baseline to beat |
|---|---|---|---|
| Vision (damage) | xBD test/holdout | per-class F1, macro-F1 | DAHiTra / ViT-on-xBD published numbers |
| Vision (flood) | FloodNet test | mIoU | FloodNet challenge baselines |
| Text triage | CrisisNLP test | accuracy / macro-F1, latency (ms/item) | CrisisSense-LLM-style classifier |
| Cross-modal verifier | Curated contradiction set (synthetic + AP regional) | precision/recall on correct contradiction resolution | Rule-based baseline (this repo's Phase 0/1 `CrossModalVerifier`) |
| Routing | Synthetic damage scenarios over real road graphs | route validity %, avg. time-to-reach for high-priority nodes | Dijkstra baseline (this repo), plain GNN-routing-with-known-damage papers |
| Full pipeline | End-to-end scenario suite | time-to-action-plan, plan correctness (human eval) | Simulated "manual EOC correlation" baseline |

## Regional generalization (key differentiator)

Report all of the above **twice**: once on the public benchmark test splits, and
once on the Andhra Pradesh regional dataset, to directly support the abstract's
claim about non-US building typologies and flood-specific text. A large gap
between public-benchmark and regional performance is itself a paper-worthy
finding (motivates fine-tuning/domain-adaptation strategy).

## Agentic orchestration evaluation (DORA / DisasterBench alignment)

Since the abstract explicitly cites DORA and DisasterBench as showing LLM agents
fail at reliable multi-step tool orchestration in disaster scenarios:
- Adopt/replicate a subset of their evaluation scenarios if licensing/access allows.
- At minimum, build an internal failure-injection suite for Phase 4:
  - a perception agent times out or errors,
  - a perception agent returns low-confidence/contradictory evidence,
  - the knowledge graph has no safe route to a high-priority location,
  - concurrent/duplicate reports for the same location arrive out of order.
- Track: does the orchestrator degrade gracefully (still produce a safe,
  clearly-caveated action plan) instead of crashing or hallucinating certainty?

## Reporting checklist for the paper

- [ ] Per-component metrics vs. named baselines (table above)
- [ ] Ablation: rule-based vs. learned cross-modal verifier
- [ ] Ablation: Dijkstra vs. GNN routing
- [ ] Public benchmark vs. AP regional dataset comparison
- [ ] End-to-end latency budget (per stage + total), relevant to the "golden window" claim
- [ ] Failure-injection results for the orchestrator (Phase 4)
