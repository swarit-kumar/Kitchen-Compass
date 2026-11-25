
# KitchenCompass – Deployment Guide

## Overview

KitchenCompass is a Streamlit application that can run locally or be hosted using Streamlit Community Cloud.

The application entry point is:

```text
app.py
```

## Environment

| Component | Requirement |
|---|---|
| Python | 3.11.x |
| Framework | Streamlit |
| Dependencies | requirements.txt |
| Main file | app.py |
| Hosting | Streamlit Community Cloud |

The project requires Python >=3.11 and <3.12.

## Local deployment

From the project root, create and activate a virtual environment:

```cmd
python -m venv .venv
.venv\Scripts\activate
```

Install the dependencies:

```cmd
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

Start the application:

```cmd
python -m streamlit run app.py
```

The application will normally be available at:

```text
http://localhost:8501
```

## Streamlit Community Cloud

The project is configured for deployment through Streamlit Community Cloud.

The deployment uses the GitHub repository:

https://github.com/swarit-kumar/Kitchen-Compass

### Deployment configuration

- Repository: `swarit-kumar/Kitchen-Compass`
- Branch: `main`
- Main file path: `app.py`
- Python version: 3.11
- Dependencies: `requirements.txt`

### Updating the deployed application

When changes are pushed to the connected GitHub branch, Streamlit Community Cloud detects the new commit and normally starts a new deployment automatically.

After pushing changes:

1. Open the Streamlit Community Cloud dashboard.
2. Select the KitchenCompass application.
3. Check the deployment status.
4. Wait for the application to finish restarting.
5. Open the application and verify the updated version.

If automatic deployment does not start, check the deployment logs and repository configuration.

## Application data and session behavior

The application uses the recipe catalogue and precomputed feature files included in the repository.

Normal application usage does not require downloading recipe or FlavorDB data.

Custom recipes are maintained in the current Streamlit session. They are not permanently added to the shared recipe catalogue.

Users can export custom recipes as JSON and import them in another session.

## Verification checklist

Before presenting or releasing an updated version, verify the following:

- [ ] The application starts without errors.
- [ ] Pantry recommendations return results.
- [ ] Ingredient exclusions are respected.
- [ ] Single substitutions return suggestions or a clear explanation.
- [ ] Joint replacement produces valid plans or explains why none are available.
- [ ] Custom recipes can be created and imported.
- [ ] Custom recipe JSON export works.
- [ ] The interface is readable and all navigation sections work.
- [ ] The automated test suite passes.
- [ ] The deployed application reflects the latest GitHub commit.

## Security and configuration

The current application does not require private API credentials for its normal operation.

Do not commit passwords, access tokens or other private credentials to the repository.

## Deployment record

Repository: https://github.com/swarit-kumar/Kitchen-Compass

Branch: `main`

Application entry point: `app.py`

Latest recorded UI commit: `156f018`

Hosting provider: Streamlit Community Cloud
