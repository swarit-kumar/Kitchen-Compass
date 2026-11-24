# KitchenCompass Phase 6 deployment

## Release configuration

- Hosting target: Streamlit Community Cloud (subject to the smoke check below).
- Application entry point: `app.py`.
- Python: 3.11 (the project requires `>=3.11,<3.12`).
- Dependencies: install from the pinned `requirements.txt`.
- Secrets: none are required by the current application. Do not add private credentials to the repository.
- Data: the read-only catalogue, frozen feature snapshot and manifest are packaged in the repository. The application does not download or modify source data at runtime.

## Cache and session behavior

`kitchencompass.service.get_catalog` caches only the read-only catalogue. The Streamlit application cache key includes the data version, config version and SHA-256 digest of `artifacts/manifest.json`. Custom recipes and drafts are stored only in the current Streamlit session state; they are not written to the catalogue, files, global caches or durable account storage.

A custom recipe is lost when its session ends unless the user downloads its JSON export. Users can import that JSON in a later session. A new browser session must begin with an empty custom-recipe list.

## Local smoke check

From the project root, with Python 3.11 and dependencies installed:

```powershell
python -m pytest -q
python -m streamlit run app.py
```

Confirm the app opens and complete the workflow checklist below before deploying.

## Streamlit Community Cloud setup

1. Push the reviewed release branch to the GitHub repository.
2. In Streamlit Community Cloud, create an app from that repository and select the release branch.
3. Set the main file path to `app.py`.
4. Use the repository's pinned `requirements.txt`; do not install unpinned packages manually.
5. Deploy and record the generated public URL and release commit below.

If the deployment smoke check fails, do not claim a successful release. Record the failure and select/document an equivalent host before release.

## End-to-end release checklist

- [ ] Pantry recommendation returns results and a no-result message for an impossible request.
- [ ] Single-ingredient substitution returns candidates or a clear no-result message.
- [ ] Joint replacement returns valid plans or a clear no-result message.
- [ ] Custom recipe creation requires ingredient confirmation.
- [ ] Custom recipe JSON export downloads a valid schema-versioned file.
- [ ] A second fresh browser session cannot see the first session's custom recipes.
- [ ] Importing the exported JSON restores the recipe in the second session.
- [ ] Data and model/config versions are visible in the sidebar.
- [ ] Evidence and uncertainty warnings remain visible.
- [ ] Loading and error feedback are visible during service requests and failures.
- [ ] Both teammates complete the deployed workflows.

## Release record

- Deployed URL: **pending deployment**
- Hosting provider: **pending smoke check**
- Release commit: **pending release commit**
- Python version: **3.11**
- Dependency file: `requirements.txt`
- Fresh-browser verification: **pending**
- Teammate verification: **pending**
