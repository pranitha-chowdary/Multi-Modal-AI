# Evaluation protocol

## Per-component benchmarks

| Component | Dataset(s) | Metric(s) | Baseline to beat | Reference |
|---|---|---|---|---|
| Vision (damage) | xBD test/holdout | per-class F1, macro-F1 | DAHiTra / ViT-on-xBD published numbers | [xBD][xbd], [DAHiTra][dahitra], [ConvNeXT multi-modal attention][convnext-attn] |
| Vision (flood) | FloodNet test | mIoU | FloodNet challenge baselines | [FloodNet][floodnet] |
| Text triage | CrisisNLP test | accuracy / macro-F1, latency (ms/item) | CrisisSense-LLM-style classifier | [CrisisSense-LLM][crisissense] |
| Cross-modal verifier | Curated contradiction set (synthetic + AP regional) | precision/recall on correct contradiction resolution | Rule-based baseline (this repo's Phase 0/1 `CrossModalVerifier`) | [3M multimodal pipeline][3m-pipeline] (MLLM-based fusion, comparable approach) |
| Routing | Synthetic damage scenarios over real road graphs | route validity %, avg. time-to-reach for high-priority nodes | Dijkstra baseline (this repo), plain GNN-routing-with-known-damage papers | [Edge-GNN road ranking][edge-gnn], [GNN-SDE evacuation routing][gnn-sde] |
| Full pipeline | End-to-end scenario suite | time-to-action-plan, plan correctness (human eval) | Simulated "manual EOC correlation" baseline | [DORA benchmark][dora] |

[xbd]: https://arxiv.org/abs/1911.09296 "xBD: A Dataset for Assessing Building Damage from Satellite Imagery"
[dahitra]: https://arxiv.org/abs/2208.02205 "Large-scale Building Damage Assessment using a Novel Hierarchical Transformer Architecture (DAHiTra)"
[convnext-attn]: https://arxiv.org/abs/2606.14963 "Multi-Modal Attention for Automated Disaster Damage Assessment Using Remote Sensing Imagery and Deep Learning"
[floodnet]: https://arxiv.org/abs/2012.02951 "FloodNet: A High Resolution Aerial Imagery Dataset for Post Flood Scene Understanding"
[crisissense]: https://arxiv.org/abs/2406.15477 "CrisisSense-LLM: Instruction Fine-Tuned LLM for Multi-label Social Media Text Classification"
[3m-pipeline]: https://arxiv.org/abs/2506.03360 "A Multimodal, Multilingual, and Multidimensional Pipeline for Fine-grained Crowdsourcing Earthquake Damage Evaluation"
[edge-gnn]: https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0296045 "Edge-based graph neural network for ranking critical road segments in a network"
[gnn-sde]: https://arxiv.org/html/2501.09803 "Graph Neural Networks for Travel Distance Estimation and Route Recommendation Under Probabilistic Hazards"
[dora]: https://arxiv.org/abs/2605.11633 "Can LLM Agents Respond to Disasters? Benchmarking Heterogeneous Geospatial Reasoning in Emergency Operations (DORA)"


## Regional generalization (key differentiator)

Report all of the above **twice**: once on the public benchmark test splits, and
once on the Andhra Pradesh regional dataset, to directly support the abstract's
claim about non-US building typologies and flood-specific text. A large gap
between public-benchmark and regional performance is itself a paper-worthy
finding (motivates fine-tuning/domain-adaptation strategy).

## Agentic orchestration evaluation (DORA / DisasterBench alignment)

Since the abstract explicitly cites [DORA][dora] and DisasterBench as showing LLM agents
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
