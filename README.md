# KitchenCompass

KitchenCompass is a pantry-based recipe recommendation and context-aware ingredient adaptation project.

The application allows users to enter available ingredients, specify exclusions, discover suitable recipes, and create their own custom recipes.

## Project status

- Phase 1: Data audit and preparation completed.
- Phase 2: Initial pantry recommendation and custom recipe implementation completed.
- Full test suite: **19 tests passed** on Windows with Python 3.11.

## Features

### Pantry-based recommendations
- Ingredient name and alias normalization.
- Canonical ingredient ID resolution.
- Pantry-based recipe ranking.
- Weighted ingredient coverage scoring.
- Display of matched and missing ingredients.
- Up to five recommendations.

### Ingredient exclusions
- Exclusions are enforced as hard constraints.
- Nested compound relationships are expanded.
- Example: excluding milk also excludes ingredients such as butter and ghee through their component relationships.

### Custom recipes
- Create custom recipes with ingredients and instructions.
- Validate recipe input.
- Generate UUID-based recipe IDs.
- Store recipes in the current application session.
- Export and import custom recipes using schema-versioned JSON.

Custom recipes remain separate from the shared recipe catalogue.

## Technology stack

- Python 3.11
- Streamlit
- Pydantic
- NumPy
- Pandas
- Pytest

## Set up on Windows

Extract the project ZIP into a folder and open CMD inside the `KitchenCompass` directory containing `app.py`.

Create a virtual environment:

```cmd
py -3.11 -m venv .venv
```

Install dependencies:

```cmd
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Install the project:

```cmd
.venv\Scripts\python.exe -m pip install -e . --no-deps
```

Run the tests:

```cmd
.venv\Scripts\python.exe -m pytest -q
```

Expected result for the current implementation:

`19 passed`

Start the application:

```cmd
.venv\Scripts\python.exe -m streamlit run app.py
```

Open `http://localhost:8501` in your browser.

To stop the application, press `Ctrl+C` in CMD.

On subsequent runs, reuse the existing `.venv` and start Streamlit directly.

**Important:** Do not run data preparation or feature-building scripts during normal setup. The existing raw snapshots, processed catalogue and benchmark splits should be preserved.

## Project structure

| Path | Contents |
|---|---|
| `app.py` | Streamlit application |
| `kitchencompass/normalize.py` | Ingredient normalization |
| `kitchencompass/constraints.py` | Ingredient exclusions and compound expansion |
| `kitchencompass/recommend.py` | Recommendation ranking |
| `kitchencompass/service.py` | Shared application service layer |
| `kitchencompass/custom_recipes.py` | Custom recipe validation and JSON handling |
| `kitchencompass/schemas.py` | Data models and result contracts |
| `data/raw/` | Original and expanded raw snapshots |
| `data/benchmark/` | Development cases, splits and review sheets |
| `scripts/` | Data preparation and feature-building scripts |
| `tests/` | Automated tests |
| `docs/` | Project documentation and implementation plans |
| `results/` | Data audit and verification records |
| `artifacts/` | Project manifest and generated artifacts |
| `HANDOFF.md` | Project implementation status and handoff notes |

## Dataset information

The active catalogue contains:

- 212 eligible recipes.
- 162 canonical ingredient records.
- 118 curries and 94 soups.
- 124 training recipes.
- 45 development recipes.
- 43 test recipes.

Related recipe groups remain within the same split.

Some recipes are AI-assisted drafts and have not been independently source-validated or cooking-tested. FlavorDB coverage is currently limited to five ingredient profiles.

Refer to `docs/DATA_SOURCES.md` and `HANDOFF.md` for provenance, limitations and review status.

## Recommendation scoring

The current weighted recommendation score is:

`score = 0.8 * weighted_coverage + 0.2 / (1 + missing_count)`

Essential ingredients receive weight 2; other ingredients receive weight 1.

Recommendations are sorted by descending score, ascending missing ingredient count, and recipe ID.

## Current limitations

- Independent development benchmark reviews are pending.
- Ingredient roles and essential-ingredient definitions require team review.
- FlavorDB coverage is incomplete.
- Exclusions are not certified allergy protection.
- Custom recipes are session-private unless exported.

The test split must remain held out from ranking adjustments.

## Team

- Phase 2 lead: Swarit
- Reviewer: Vibhu Shriwal