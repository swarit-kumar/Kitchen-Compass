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
