# KitchenCompass decisions

| ID | Decision | Status |
|---|---|---|
| P0-01 | Python 3.11, Streamlit, Pydantic and pytest | In use. Vibhu reported all nine tests passed on Windows on the previous 34-recipe checkpoint. |
| P0-02 | Early hosting smoke test | Open. No deployment URL has been recorded. |
| P1-01 | Preserve the original generated recipe snapshot | Implemented. Its SHA-256 is recorded in the v2 snapshot and manifest. |
| P1-02 | Expand toward 200 eligible soups and curries | Met. 212 eligible recipes, with 162 ingredient records including component-only entries. |
| P1-03 | Use project-specific formulations for known compounds | Implemented for team review. Twelve in-scope records with unresolved compositions are excluded. |
| P1-04 | Keep related recipes together and train features on the training split | Implemented. The v2 split uses seed 42 and supersedes the pilot split. |
| P1-05 | Keep the five verified FlavorDB profiles and represent unavailable profiles explicitly | Implemented. Broader coverage is needed for Phase 3 flavor evaluation. |
| P1-06 | Archive v1 development cases and use new v2 cases with a shared candidate pool | Implemented. Independent labels and agreement are pending. |

The course deadline, hosting status and team availability can be recorded
during the handoff.

## 20 November 2026 · Phase 2 fixes and Phase 3 implementation

| ID | Change and reason | Affected files | Review |
|---|---|---|---|
| P2-01 | Introduce a separately selectable plain-overlap comparator. Sort rankings on unrounded scores, identify data/config versions, and hash the exact LF bytes used in the ZIP. | recommend.py, service.py, .gitattributes, scripts/build_features.py, tests/test_recommend.py | Implemented for Vibhu. Swarit review pending. |
| P2-02 | Resolve custom entries before saving or ranking. Allow confirmed IDs and essential flags. Export format 2.0 identifies the extension; importing format 1.0 upgrades in memory and preserves the UUID, original phrases, quantities and instructions. | custom_recipes.py, service.py, app.py, tests/test_custom_recipe.py | Implemented for Vibhu. Swarit review pending. |
| P3-01 | Use the fixed plan weights and held-out development cases. Keep missing molecular evidence explicit and use the existing five molecular snapshots. Provide the four controlled comparisons and score breakdowns. No weight tuning was performed. | catalog.py, features.py, roles.py, substitute.py, config/settings.json, scripts/evaluate.py, tests/test_substitute.py | Implemented for Vibhu. Swarit review pending. |
| P3-02 | Permit narrowly scoped, source-checked preparation rules. Partial role matches need an ingredient and dish family. Contextual pair blocks apply to all model variants. These are implementation judgments; human benchmark grading remains independent. | data/curation/substitution_policy.json, data/processed/substitution_pairs.jsonl, docs/PHASE_3.md | Codex checked the cited preparation sources. Team sign-off pending. |

## 23 November 2026 · Phase 4

The public service and the Streamlit joint screen share the bounded exhaustive planner and an independent final validator. The benchmark runner now evaluates the four original joint development prompts and retains abstentions. Positive pair scores and hard blocks require a reviewed entry with evidence and a reviewer. The onion–celery proposal remains pending; all release pair scores therefore use the training vectors. The distinct model, catalogue and release version numbers identify different parts of the snapshot.

## 23 November 2026 · Phase 5

| ID | Decision and reason | Files and review |
|---|---|---|
| P5-01 | Keep the grouped recipe splits and Phase 4 model unchanged. Construct 150 distinct scenarios and pool options from all methods for blinded human review. A development pilot lacked common flavor-evidence comparisons, so a declared subset uses measured targets and candidate availability. Lock this design before final test evaluation. | phase5 case files, benchmark.py, experiments.py, protocol_lock.json. Implemented for Vibhu and Swarit. |
| P5-02 | Publish development coverage and constraint metrics while the review sheets are blank. Defer final test evaluation until original human ratings, pre-reconciliation agreement, resolved labels and file hashes are recorded. Store observed timings separately from deterministic ranking outputs. | annotations.py, experiment_metrics.py, scripts/evaluate.py, docs/EVALUATION.md. Final human review pending. |
