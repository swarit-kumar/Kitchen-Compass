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
