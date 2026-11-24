# KitchenCompass

KitchenCompass runs locally in your browser. It finds soup and curry recipes from a pantry, saves custom recipes in the current session and ranks replacements for one to three ingredients together. The release includes 212 recipes, 162 catalogue ingredients and prebuilt features for offline use after installation.

## Phase 5 benchmark

The release includes 150 frozen study cases, blinded grading sheets for Vibhu and Swarit, development comparisons and a latency benchmark. The four-screen application works as before. The evaluation runs from PowerShell.

Use [the evaluation guide](docs/EVALUATION.md) to read the development results, fill the two review sheets, reconcile disagreements and produce the final test report. The downloaded checkpoint is at the human-review stage. To see current progress from the project folder, run this command.

```powershell
.\.venv\Scripts\python.exe scripts\benchmark.py status
```

## First run on Windows

Download the release ZIP into Downloads. In PowerShell, extract it into a new folder alongside your previous project.

```powershell
Expand-Archive -LiteralPath "$HOME\Downloads\KitchenCompass_P05_v0.6.0_20261123.zip" -DestinationPath "D:\KitchenCompass"
Set-Location "D:\KitchenCompass\KitchenCompass_Phase5_v0.6.0"
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If you extracted the ZIP manually, open PowerShell in the folder containing `app.py` and begin at the virtual environment command. If the Python launcher cannot find 3.11, run `python --version`. When it reports Python 3.11.x, use `python -m venv .venv` in place of the launcher command. A known working Python 3.11 executable can also create this environment by its full path.

Open `http://localhost:8501` if the browser does not open automatically. Use the Local URL printed by Streamlit if the port differs. Keep PowerShell open while presenting. Press Ctrl+C there to stop the server.

## Run it next time

```powershell
Set-Location "D:\KitchenCompass\KitchenCompass_Phase5_v0.6.0"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Professor demo

Follow [the walkthrough](docs/DEMO_WINDOWS.md) for the inputs, expected results and a short explanation of each screen. Start with **Pantry search**, then open **Substitutions** in the sidebar. Four examples load reproducible inputs. Press **Find substitutes** after loading an example or changing a method. Click **View recipe** on a pantry result to read its ingredients and numbered cooking steps. **Hide recipe** collapses the details. Both search screens show up to five results initially. Use **Show 5 more** below the results to reveal the next batch. The final batch shows the remaining results.

Open **Joint replacements**, choose **Paneer and pepper**, then **Find replacement plans**. The two eligible plans replace both targets. Try **Chowder comparison** and expand **Compare with independent choices** to see why choosing each target separately can reuse the same replacement.

**Custom recipes** supports entry and JSON import, explicit confirmation of ingredient names, instructions and quantities, optional essential flags and JSON download. A session can use a custom recipe immediately in the single or joint replacement screen.

## Reproduce the development run

Run these from the extracted project folder in PowerShell. The ZIP already includes the outputs needed for the demo.

```powershell
.\.venv\Scripts\python.exe scripts\expand_recipes.py --check
.\.venv\Scripts\python.exe scripts\prepare_data.py --config config\settings.json
.\.venv\Scripts\python.exe scripts\build_features.py --config config\settings.json
.\.venv\Scripts\python.exe scripts\evaluate.py --split dev --config config\settings.json
.\.venv\Scripts\python.exe -m pytest -q
```

[Phase 4 implementation and results](docs/PHASE_4.md) · [Phase 3 results and methods](docs/PHASE_3.md) · [Team handoff](HANDOFF.md) · [Data sources](docs/DATA_SOURCES.md)
