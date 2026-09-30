# Dataset acquisition guide

Start these registrations/downloads as early as possible (Phase 1) — approval and
download can take longer than the model training itself.

## 1. xBD (xView2) — building damage assessment
- Paired pre/post-disaster satellite imagery with building polygons labeled
  `no-damage / minor-damage / major-damage / destroyed`.
- Official project: xView2 (search "xView2 xBD dataset" — hosted at xview2.org).
  Registration required to download the full imagery; a devkit/labels sample
  may be available without registration.
- Use for: Vision agent (`adis.perception.vision`) fine-tuning + Phase 5 benchmark.
- Note the project's stated gap: xBD is inherently *paired* pre/post imagery.
  Design your training/eval split to also test **post-only / unpaired** inference,
  since live disaster response often lacks a clean "before" image.

## 2. FloodNet — flood segmentation
- UAV/drone imagery with pixel-level flood segmentation and classification labels.
  Search "FloodNet dataset" (IEEE GRSS / University of Virginia release).
- Use for: flood-level segmentation head of the vision agent.

## 3. CrisisNLP — social media crisis text
- Multiple labeled crisis-tweet corpora (informativeness, humanitarian category,
  damage severity) from QCRI's CrisisNLP project (crisisnlp.qcri.org).
- Use for: text triage agent (`adis.perception.text`) fine-tuning + Phase 5 benchmark.
- Filter/augment for **flood-specific** vocabulary and non-English-heavy or
  code-mixed (e.g. Telugu-English) text if you plan to reuse this data as a
  proxy for the AP regional corpus during early development.

## 4. Andhra Pradesh regional dataset (to be curated)
This is the project's key differentiator — plan for it as its own workstream,
not an afterthought:
- **Imagery**: satellite/drone imagery of flood-prone AP districts (e.g. from
  open government/Copernicus/Sentinel sources where licensing permits, or
  drone capture if you have field access). Label with the same damage-level
  taxonomy as xBD for transfer compatibility.
- **Text**: local social media / helpline call transcripts, ideally with
  Telugu and code-mixed Telugu-English examples, labeled with the same
  taxonomy as CrisisNLP.
- **Geospatial**: road network + hospital/shelter locations for at least one
  target district, via OpenStreetMap (`osmnx`) plus manual correction, since
  OSM completeness varies significantly by region.
- **Ethics/licensing**: get institutional review/consent guidance before
  collecting/publishing any real emergency-call or social-media text data,
  especially anything containing personal information.

## 5. Related work references (papers — not downloadable raw data)
These were checked for usable raw feed data; none expose downloadable images or
un-redacted text directly, but they're useful as model/architecture baselines
(see [docs/evaluation.md](evaluation.md) for how each maps to a benchmark):
- [xBD paper](https://arxiv.org/abs/1911.09296), [DAHiTra](https://arxiv.org/abs/2208.02205),
  [ConvNeXT multi-modal attention](https://arxiv.org/abs/2606.14963) — vision/damage baselines.
- [FloodNet paper](https://arxiv.org/abs/2012.02951) — flood segmentation baseline.
- [CrisisSense-LLM](https://arxiv.org/abs/2406.15477) — text triage baseline.
- [3M multimodal earthquake pipeline](https://arxiv.org/abs/2506.03360) — its
  [GitHub repo](https://github.com/missa7481/EMNLP25_earthquake) has sample result
  CSVs but explicitly states raw tweet text/user data was redacted ("full dataset
  available upon request") — not a usable raw-feed source without contacting the authors.
- [DORA benchmark](https://arxiv.org/abs/2605.11633) — orchestrator/agent evaluation baseline.
- [Edge-GNN road ranking](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0296045),
  [GNN-SDE evacuation routing](https://arxiv.org/html/2501.09803) — routing agent baselines.

## Suggested local layout

```
data/
  raw/
    xbd/
    floodnet/
    crisisnlp/
    ap_regional/
  processed/
    xbd/           # resized tiles, train/val/test splits
    floodnet/
    crisisnlp/
    ap_regional/
    road_network/  # osmnx-extracted graphs per region
```

`data/raw/` and `data/processed/` are gitignored — do not commit raw imagery/text
into the repo; keep large artifacts out of git (use DVC/cloud storage if you need
dataset versioning later).
