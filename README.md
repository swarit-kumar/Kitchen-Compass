
# KitchenCompass

KitchenCompass is a computational gastronomy project for recipe
recommendation, context-aware ingredient substitution, and constrained
recipe adaptation.

## Current status

Phase 0: project setup. Recipe data and recommendation algorithms
have not yet been implemented.

## Requirements

- Python 3.11
- Git
- Dependencies listed in requirements.txt

## Setup on Windows

    py -3.11 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    .\.venv\Scripts\python.exe -m pip install -e . --no-deps

## Run tests

    .\.venv\Scripts\python.exe -m pytest -q

## Run the application

    .\.venv\Scripts\python.exe -m streamlit run app.py

## Project scope

The initial application shell is a setup milestone only.
Do not interpret it as evidence that recipe recommendations,
substitutions, or adaptations are working.
