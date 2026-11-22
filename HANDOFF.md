# KitchenCompass handoff · Phase 4

| Item | Checkpoint |
|---|---|
| Plan | Shared Implementation and Handoff Plan 1.0, included in `docs/` |
| Original snapshot | P03-v0.4.2-20261120 · ZIP handoff |
| Current state | Phase 4 implementation complete · pending manual evidence review |
| Sender / receiver | Vibhu / Swarit |
| Phase 4 ownership | Lead: Vibhu · Reviewer: Swarit |
| Parent | Swarit’s `Kitchen-Compass-main.zip`, SHA-256 `2ecccff9be475984c9cf307e5891434f965addcc30a25a3308af56ca684c74c9` |
| Catalogue / config / benchmark | 2.0 / 0.4.0 / groups_seed_42_v2 |
| Schemas | Catalogue and result envelope 1.0. Custom recipe export 2.0 reads earlier 1.0 inputs. |
| Environment | CPython 3.11.18 recorded in manifest. Phase 4 regression suite verified on Windows. |
| Latest verification | `python -m pytest -q` → 99 passed in 8.24s |
| GitHub status | Phase 4 changes are in the extracted working directory. Transfer to the original Git repository is pending. |

## Changes through Phase 3

The Phase 3 implementation and history are retained.

- Added a separately callable overlap baseline and corrected ranking to sort on full-precision scores. Both pantry methods use the same exclusions, including compound ingredients.
- Rebuilt hashes against distributed LF files and set an explicit Git line-ending rule.
- Added ingredient confirmation for custom entry and import. Original wording, quantity, essential flags, instructions and UUID survive export/import.
- Added a frozen catalogue loader and single-target service, instruction-based roles, molecular Jaccard, training-only context cosine, hard filters, optional purchases and ranked explanations.
- Integrated the screens, demo examples, development runner and regression tests.
- Pantry search and substitutions show five ranked results initially and reveal more on request. Each pantry result has a View recipe button.
- The earlier Phase 3 notes and decisions remain in `docs/PHASE_3.md` and the decision log.

## Phase 4 · Joint ingredient adaptation

### Objective

Extend single-target substitution into joint adaptation for one to three ingredient targets.

Main implementation: `kitchencompass/adapt.py`

Implemented functions:

- `validate_targets`
- `generate_candidate_lists`
- `target_role_context`
- `pair_compatibility_score`
- `score_joint_plan`
- `generate_joint_plans`
- `generate_independent_baseline`
- `validate_plan`

### Planning limits

- Maximum targets: 3.
- Maximum candidates per target: 5.
- Maximum combinations: 125.
- Replacement IDs must be distinct.
- Target ingredients cannot be selected as replacements.
- Requested targets must be covered exactly once.
- Exclusions, pantry restrictions and replacement limits are validated.

### Joint scoring

For multiple replacements:

`Plan score = 0.8 × Q + 0.2 × J`

Where:

- Q = mean individual substitution score.
- J = mean pair-compatibility score.

For a single replacement, the individual score is used.

Pair compatibility is a computational proxy, not a guarantee of culinary suitability. Hard-block rules take precedence. Missing or zero-vector evidence is handled conservatively and reported.

### Independent baseline

The baseline selects the individually highest-scoring candidate for each target from the same candidate lists.

It does not silently repair duplicate replacement IDs or incompatible pairs. Such violations are reported so the joint planner can be compared fairly against independent selection.

### Independent validation

`validate_plan` checks the completed plan, including:

- Exact target coverage.
- Replacement distinctness.
- Unknown or invalid ingredient IDs.
- Exclusions and pantry restrictions.
- Replacement limits.
- Retained ingredient duplication.
- Blocked replacement pairs.

### Development results

Generated output: `results/development_joint_plans.json`

Four two-target development cases were generated:

| Case | Targets | Joint plans | Valid plans | Baseline |
|---|---|---:|---:|---|
| dev_v2_09 | Cauliflower, grated coconut | 2 | 2 | Invalid |
| dev_v2_10 | Small pasta, celery | 2 | 2 | Invalid |
| dev_v2_10 | Small pasta, canned tomato | 2 | 2 | Invalid |
| dev_v2_10 | Small pasta, cooked chickpea | 2 | 2 | Invalid |

All four cases have `pending_review` status.

These results demonstrate planner behavior and validation, not manually verified culinary recommendations. Candidate evidence still requires review.

### Service integration boundary

The existing public service functions remain:

- `recommend_recipes`
- `recommend_for_pantry`
- `rank_substitutes`

The Phase 4 joint planner currently exists as a module-level implementation in `adapt.py`. A public joint-adaptation endpoint in `service.py` has not been implemented.

The existing `Result` schema supports:

- `OK`
- `NEEDS_INPUT`
- `UNSUPPORTED_INPUT`
- `UNRESOLVED_EXCLUSION`
- `NO_FEASIBLE_RESULT`

Do not claim that joint adaptation is already exposed through this response contract.

## Phase 4 files added or updated

| File | Purpose |
|---|---|
| `kitchencompass/adapt.py` | Joint planner, scoring and validation |
| `tests/test_adapt.py` | Phase 4 tests |
| `scripts/check_joint_cases.py` | Development joint-plan generation |
| `scripts/update_phase4_manifest.py` | Safe Phase 4 manifest updater |
| `results/development_joint_plans.json` | Development joint-plan results |
| `docs/PHASE_4.md` | Phase 4 implementation notes |
| `docs/SERVICE_CONTRACT_EXAMPLES.md` | Service schema examples |
| `artifacts/manifest.json` | Updated Phase 4 hashes and status |

The manifest updater preserves existing Phase 1–3 entries and adds Phase 4 input and output hashes.

## Verification

Latest full regression run:

`python -m pytest -q`

Result:

`99 passed in 8.24s`

Manifest JSON validation:

`python -m json.tool artifacts/manifest.json`

Result: successful.

Development output JSON validation:

`python -m json.tool results/development_joint_plans.json`

Result: previously successful.

## Remaining tasks

1. Complete manual review of the four development cases and reconcile both teammates' judgments.
2. Review candidate evidence and pair-compatibility rules. Do not present pending-review outputs as validated culinary advice.
3. Decide whether a public joint-adaptation service endpoint is required in the next phase.
4. Complete the final required-file and output verification.
5. Transfer the Phase 4 changes from the extracted ZIP working directory into the original Git repository.
6. Review the updated handoff and record receiver acceptance.

## Instructions for the next teammate

Start by reading:

- `docs/PHASE_4.md`
- `docs/SERVICE_CONTRACT_EXAMPLES.md`
- `docs/PHASE_3.md`
- `docs/DECISIONS.md`
- `results/development_joint_plans.json`

Run the complete test suite before making changes:

`python -m pytest -q`

Do not rebuild Phase 1–3 features just to update the manifest. Use `scripts/update_phase4_manifest.py` after relevant Phase 4 file changes.

Keep pending-review evidence clearly separated from manually validated results. Do not fabricate culinary evidence, ingredient conversions or cooking-instruction changes.

The Phase 3 handoff history is retained in this document's earlier project records and the Phase 2 handoff remains available at `docs/history/PHASE_2_HANDOFF.md`.
