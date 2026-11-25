
# KitchenCompass

KitchenCompass is a recipe recommendation and ingredient substitution application developed as part of a Computational Gastronomy project.

The application helps users find recipes based on ingredients they already have and adapt recipes when certain ingredients are unavailable or excluded. It also supports replacing multiple ingredients together and working with custom recipes.

The application is built with Python and Streamlit.

## Features

### 1. Pantry-based recipe recommendations
- Enter ingredients available in your kitchen.
- Exclude ingredients you do not want to use.
- Get recipes ranked according to ingredient availability.
- Compare weighted matching with simple ingredient overlap.
- View available and missing ingredients for each recipe.

### 2. Ingredient substitution
- Select a recipe and an ingredient to replace.
- Get ranked replacement suggestions.
- Consider flavor similarity, ingredient roles and recipe context.
- Apply pantry and exclusion constraints.
- View explanations and evidence behind recommendations.

### 3. Joint ingredient replacement
- Replace multiple ingredients in a recipe together.
- Generate complete replacement plans.
- Check whether replacement ingredients satisfy the constraints.
- Compare joint replacement plans with independent ingredient choices.

### 4. Custom recipes
- Enter a recipe manually or import it using JSON.
- Review and confirm ingredient names.
- Preserve ingredient quantities and cooking instructions.
- Use custom recipes in the substitution workflows.
- Export recipes as JSON.

## Project data

The current packaged dataset contains:
- 212 eligible recipes.
- 162 canonical ingredient records.
- Five ingredient profiles with available molecular evidence from FlavorDB.
- Precomputed ingredient and recipe context features.

The recipe catalogue and feature files are included in the project. The application does not need to download the source data every time it runs.

FlavorDB evidence is currently limited to a small number of ingredients. Recommendations should therefore be interpreted as suggestions rather than guaranteed culinary equivalents.

See [Data Sources](docs/DATA_SOURCES.md) for dataset details and attribution.

## Technology stack

- Python 3.11
- Streamlit
- Pydantic
- NumPy
- Pandas
- Pytest

## Requirements

- Python 3.11.x
- pip
- Git (optional, for cloning the repository)

The project requires Python >=3.11 and <3.12.

## Installation and setup

### Windows

Open Command Prompt in the project folder.

Create a virtual environment:

```cmd
python -m venv .venv
```

Activate it:

```cmd
.venv\Scripts\activate
```

Upgrade pip:

```cmd
python -m pip install --upgrade pip
```

Install dependencies:

```cmd
python -m pip install -r requirements.txt
```

Install the project package:

```cmd
python -m pip install -e . --no-deps
```

## Run the application

Start the Streamlit application:

```cmd
python -m streamlit run app.py
```

Open the local URL shown in the terminal. Usually:

```text
http://localhost:8501
```

Keep the terminal open while using the application.

To stop the application, press `Ctrl + C`.

## Run the tests

From the project root, execute:

```cmd
python -m pytest -q
```

The latest recorded full test run after the UI updates completed with:

```text
128 passed
```

## Rebuild the data and features

The project includes scripts for preparing recipe data and generating features.

Run the following commands when a full rebuild is required:

```cmd
python scripts\expand_recipes.py --check
python scripts\prepare_data.py --config config\settings.json
python scripts\build_features.py --config config\settings.json
```

Rebuilding the features also updates the project manifest. Do not modify the generated manifest manually.

## Project structure

```text
KitchenCompass/
│
├── app.py
├── kitchencompass/
│   ├── schemas.py
│   ├── service.py
│   └── ...
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── benchmark/
│   └── curation/
│
├── artifacts/
├── config/
├── docs/
├── results/
├── scripts/
├── tests/
│
├── requirements.in
├── requirements.txt
├── pyproject.toml
├── README.md
└── HANDOFF.md
```

## Evaluation status

The project includes benchmark cases, development experiments and evaluation scripts. The benchmark documentation describes the experimental setup and the human-review process.

Final human-reviewed quality results should only be reported after the assigned reviews have been completed and the test evaluation has been generated.

See [Evaluation](docs/EVALUATION.md) for details.

## Deployment

The application is configured for Streamlit Community Cloud deployment.

See [Deployment Guide](docs/DEPLOYMENT.md) for deployment information and verification steps.

## Team

KitchenCompass was developed as a two-member Computational Gastronomy project.

For implementation status, decisions and remaining work, see [HANDOFF.md](HANDOFF.md).
