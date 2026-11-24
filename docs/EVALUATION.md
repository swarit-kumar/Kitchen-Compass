# Phase 5 benchmark and experimental evaluation

**Checkpoint P05 v0.6.0.** The 150 case specifications, option pools, split, software and scoring configuration are frozen. The development experiments and runtime measurements are available now. The release contains blank human review sheets. Final test scoring, agreement and human relevance statistics await actual judgments from Vibhu and Swarit.

## What was measured

| Task | Dev cases | Test cases reserved | Comparison | Budget per request |
|---|---:|---:|---|---|
| Pantry recommendation | 25 | 25 | Weighted and simple overlap | Top 5 recipes each |
| Single substitution | 35 | 35 | Full, flavor only, without context, without roles | Top 5 each from the same constrained vocabulary |
| Joint replacement | 15 | 15 | Joint search and independent top choices | Same 5 candidates per target, at most 125 combinations, 3 ranked plans or 1 independent choice |

Both splits contain 41 distinct source recipes from 9 duplicate groups each. The catalogue has 212 recipes. The 124 training recipes alone supply the context vectors. Pantry searches use the full application catalogue. A case's split follows its source recipe group. All methods within a comparison receive the same request and settings.

The first 15 development requests come from the Phase 4 benchmark. The other 135 are deterministic requests constructed from catalogue recipes, ingredient roles, pantry availability and exclusions. They represent study scenarios, rather than a sample of actual user traffic. Source ingredient lines and instructions are identified in every case. The constructor rejects duplicate requests and balances source groups within a task. A pilot development sample had no cases with complete flavor evidence. Before issuing the first Phase 5 freeze, we reserved every fifth newly numbered single case for a recipe with a measured target and a measured alternative. There are 6 such cases on development and 7 reserved on test. Availability of molecular profiles determined selection. Ranking weights and catalogue rules carry forward from Phase 4.

The review pool contains the union of all declared methods' returned options, including single-substitution complete-evidence runs. It also contains authored options from the original 15 cases and a reference choice for each new case. Options are deduplicated by recipe ID or full replacement mapping and presented in a stable order without ranking positions or method names. Options outside the pool have unknown relevance. Building the pool requires retrieving candidate IDs on both splits. The sealed test experiment produces scores and comparative tables only after human labels are frozen.

## Development observations

| Method | Cases with results | Items returned | Hard-constraint failures |
|---|---:|---:|---:|
| Pantry weighted | 25 / 25 | 125 | 0 |
| Pantry overlap | 25 / 25 | 125 | 0 |
| Single full | 30 / 35 | 125 | 0 |
| Single flavor only | 6 / 35 | 20 | 0 |
| Single without context | 4 / 35 | 5 | 0 |
| Single without roles | 17 / 35 | 48 | 0 |
| Joint planner | 13 / 15 | 38 | 0 |
| Independent joint choices | 13 / 15 | 13 | 3 |

The full methods returned 288 items and all passed the final hard checks. Three independent joint selections reused an ingredient. On the 10 cases with both a feasible independent selection and a joint plan, the best joint plan scored 0.0347 higher on average on the model's own objective. The five-recipe pantry lists averaged 4.136 missing ingredients for weighted ranking and 4.112 for overlap. Human grading determines how practical those lists are.

Six single-substitution development cases had a candidate with flavor, context and role measured. On this common subset the full method returned results on 4/6, flavor only on 6/6, without context on 4/6 and without roles on 3/6. The catalogue contains only five measured molecular profiles. All-case coverage and common-subset quality answer different questions.

### Three cases to inspect

- **dev_v2_06, Capsicum and Paneer Masala.** The full method returned two replacements for paneer using available role and context evidence. Flavor-only abstained because it lacked the required molecular evidence.
- **dev_v2_12, Broccoli Cheddar Soup.** Independent selection chose olive oil twice. Joint selection returned three distinct, constraint-valid plans. Whether a replacement preserves the body of the soup is a judgment for the reviewers.
- **p5_dev_joint_07, Moroccan Harira.** The restricted pantry yielded no eligible replacements for red lentil and cooked chickpea. Both methods abstained. This case remains in the coverage denominator.

### Metric definitions

- **Pantry.** nDCG@5 uses exponential gain `2^grade − 1`, log base 2 discount, and the ideal five options from the entire judged pool. Cases with zero ideal gain have undefined nDCG. Missing counts are computed from ingredient IDs and averaged within each returned list. Exclusions are independently checked by following ingredient components.
- **Single.** Grade 2 is relevant. Hit@3 and reciprocal rank through position 5 use cases with at least one judged relevant option. Eligible misses and abstentions score zero. Top-three plausibility is the mean grade of returned top-three items, then averaged across nonempty judged cases. Candidate-generation recall measures the fraction of the judged relevant pool surviving the pre-role hard filter. On the complete-evidence comparison the relevant universe is restricted to that shared pool. The all-case recall reveals pre-filter losses.
- **Joint.** Report rejected independent choices with their actual mapping and violations. Grade-2 hit counts the presence of any grade-2 option in the top three, or in the single independent result. A fully reviewed abstention or miss contributes zero. The score difference only compares two feasible outputs under the same objective. Zero-vector pair evidence and duplicate failures have separate counters.
- **Uncertainty.** All reported means show eligible case counts. For a metric with at least five distinct eligible source groups, the evaluator draws 1,000 bootstrap samples of whole groups with replacement, seed 42, and reports a percentile interval. With nine groups per split, intervals are provisional. Null denotes an unavailable measurement. Violation rate uses emitted items as its denominator. Abstention rate uses evaluated requests.
- **Runtime.** The separate benchmark loads a fresh catalogue in-process, warms each development request once, then makes 100 timed calls per task, cycling over the same development cases in ID order. It measures the public full service with a shared catalogue. It records raw samples, platform, CPU count, corpus and dependencies. The cold value measures catalogue construction after imports. Local timings exclude browser, network and deployment overhead. Rankings and derived metrics are deterministic. Latency varies by machine.

## Grade the benchmark on Windows

Each teammate edits their own UTF-8 CSV under `data/benchmark/phase5/reviews/`. Give Swarit his copy separately and exchange the completed sheets after both independent reviews. Keep the case IDs, option IDs, assigned rows and column headers. Use Excel's CSV UTF-8 format when saving. If the original 15 cases already have paper or pilot grades, match each by exact case and option contents before transferring. The Phase 5 option IDs were reassigned when the pool expanded.

| Sheet | Assigned option ratings |
|---|---:|
| Vibhu.csv | 548 |
| Swarit.csv | 509 |

There are 825 distinct case-option pairs. Exactly 45 cases are assigned to both reviewers, including all 15 joint test cases. On each row fill `grade` (0, 1 or 2), `evidence_type`, `evidence_ref` and `rationale`. Use the displayed pantry, exclusions, recipe ingredients, preparation steps and candidate. For pantry questions the ingredient and instruction columns describe the **candidate recipe**.

| Evidence type | Use |
|---|---|
| recipe_practicality | Evaluate how well a candidate recipe fits the pantry. Reference its exact recipe record. |
| documented_substitution | Cite a culinary source and passage that directly documents the replacement in the relevant context. |
| plausibility_judgment | Explain your own assessment of the cooking role in this particular recipe. Reference the recipe and relevant step. |
| constraint_violation | Give grade 0 and name the conflict, such as a milk-derived ingredient or a duplicated joint replacement. |

Pantry grades mean unsuitable (0), possible with substantial additions (1), or practical (2). Substitution and joint grades mean unsuitable (0), plausible with caveats (1), or suitable for this role and preparation (2). A recipe citation establishes the preparation context. A claim of a documented substitution requires separate supporting evidence.

From the project folder, after the Windows setup in the README, run the following.

```powershell
.\.venv\Scripts\python.exe scripts\benchmark.py status
.\.venv\Scripts\python.exe scripts\evaluate.py --split dev
```

After returning the two completed sheets to the same `reviews` folder, run the reconciliation command.

```powershell
.\.venv\Scripts\python.exe scripts\benchmark.py reconcile
```

Open `reconciliation.csv`. For each disagreement, compare the two original rationales and sources together, then fill the four decision fields. Keep both original sheets. The tool computes exact agreement on the original doubly rated options before reconciliation. A rerun preserves completed decisions. Resolve every missing or invalid rating displayed by `status`. When all 150 cases are complete, run the final commands.

```powershell
.\.venv\Scripts\python.exe scripts\benchmark.py freeze-labels
.\.venv\Scripts\python.exe scripts\evaluate.py --split dev
.\.venv\Scripts\python.exe scripts\evaluate.py --split test
.\.venv\Scripts\python.exe scripts\build_features.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\package_handoff.py --phase 5 --output dist
```

The test command checks the frozen inputs and reconciled labels before ranking. The label lock includes original annotations, final judgments, agreement and source-sheet hashes. Archive the frozen sheets and outputs together. Treat a later change to cases, labels, scoring or rules as a new, explicitly exploratory experiment.

## Files to use

| File | Contents |
|---|---|
| `data/benchmark/phase5/dev_cases.jsonl`, `test_cases.jsonl` | Frozen requests, pool contents, provenance and review assignments |
| `data/benchmark/phase5/protocol_lock.json` | SHA-256 values for cases, split, configuration, processed data, features and experiment code |
| `results/per_case.jsonl` | Each dev request, ranking, score components, abstentions, warnings, validation and eligibility |
| `results/metrics.json`, `results/summary.csv` | Development comparison and machine-readable table |
| `results/runtime.json` | Measured timings and environment. Use `scripts/measure_runtime.py` for another machine's measurements in `results/runtime.local.json`. |
| `data/benchmark/phase5/labels_lock.json` | Created after review and reconciliation |
| `results/test/` | Final per-case output, metrics and summary, created by the explicit test command after freeze |

`scripts/benchmark.py prepare` verifies an existing protocol and creates missing worksheet files. It preserves existing worksheets. The older `results/development_*.json` files reproduce the Phase 4 pilot and have different denominators from the Phase 5 experiment.
