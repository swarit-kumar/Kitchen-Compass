
# KitchenCompass – Project Handoff

## Project overview

KitchenCompass is a web application for pantry-based recipe recommendation and context-aware ingredient substitution.

The project combines recipe data, ingredient information, flavor evidence and cooking-role context to generate useful recipe recommendations and replacement plans.

The application is developed using Python and Streamlit.

## Current project status

| Area | Status |
|---|---|
| Recipe catalogue | Prepared |
| Ingredient catalogue | Prepared |
| FlavorDB integration | Implemented with limited profile coverage |
| Recipe recommendation | Implemented |
| Single-ingredient substitution | Implemented |
| Joint ingredient replacement | Implemented |
| Custom recipe support | Implemented |
| Streamlit interface | Implemented and redesigned |
| Automated tests | 128 passed in the latest recorded full run |
| GitHub repository | Updated with latest UI commit |
| Streamlit deployment | Configured |
| Human-reviewed benchmark results | Pending completion |

## Application functionality

The application contains four main sections:

1. **Pantry:** recommends recipes based on available and excluded ingredients.
2. **Substitutions:** ranks possible replacements for a selected ingredient.
3. **Joint replacements:** generates plans for replacing multiple ingredients together.
4. **Custom recipes:** allows users to create, import, save during a session and export their own recipes.

The interface has been updated to improve page organization, readability, navigation and visibility of important information.

The UI changes preserve the existing application workflows and Streamlit widget keys.

## Data and implementation

- The active recipe catalogue contains 212 recipes.
- The ingredient catalogue contains 162 canonical ingredient records.
- Molecular flavor evidence is currently available for five ingredient profiles.
- Recipe context features are generated from the training split.
- The application uses packaged data and features during normal execution.
- Custom recipes are stored in the current Streamlit session and can be exported as JSON.

Refer to `docs/DATA_SOURCES.md` for data provenance and attribution.

## Verification

The latest recorded full test run after the UI changes:

```text
python -m pytest -q

128 passed
```

The application was also checked for Python syntax errors and its main workflows were manually reviewed.

The manifest was regenerated after the application changes.

## GitHub and deployment

The latest UI update was committed and pushed to the `main` branch.

Latest UI commit:

```text
156f018
```

Repository:

https://github.com/swarit-kumar/Kitchen-Compass

The Streamlit Community Cloud deployment uses the GitHub repository.

## Important limitations

- FlavorDB coverage is limited, so molecular evidence is not available for every ingredient.
- Recipe substitutions are recommendations and may require adjustments during actual cooking.
- Human review is needed to assess culinary suitability independently of automated constraint checks.
- Final benchmark quality results should not be claimed until the human-review process and held-out evaluation are complete.
- Custom recipes are session-based unless exported by the user.

## Running the project

Refer to `README.md` for the complete Windows installation and execution instructions.

To run the application:

```cmd
python -m streamlit run app.py
```

To run the test suite:

```cmd
python -m pytest -q
```

## Main documentation

- `README.md` – project description and setup.
- `docs/DATA_SOURCES.md` – data sources and attribution.
- `docs/EVALUATION.md` – benchmark and evaluation methodology.
- `docs/DEPLOYMENT.md` – deployment configuration and checks.
- `docs/DEMO_WINDOWS.md` – application demonstration guide.
- `docs/DECISIONS.md` – recorded project decisions.
