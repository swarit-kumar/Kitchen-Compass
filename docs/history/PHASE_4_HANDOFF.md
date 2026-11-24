# KitchenCompass Phase 4 handoff

| Item | Checkpoint |
|---|---|
| Release | P04-v0.5.0-20261123 |
| Parent | Swarit’s Kitchen-Compass-main(1).zip, SHA-256 `1e14fb4b4121cdf3983b5fa4e97abcb7a13603f6a5cc0bb9538e4cee0b8daadd` |
| Handoff | Prepared for Vibhu to give to Swarit. Receiver acceptance is open. |
| Scope | Phase 4 joint replacement selection and its local demo |
| Snapshot | Schema 1.0, catalogue 2.0, Phase 3 individual-scoring config 0.4.0, split groups_seed_42_v2 |
| Verification | CPython 3.11.18. See [commands and results](results/verification.txt). Native Windows sign-off for this release remains open. |
| Development run | 4 official joint cases, 11 plans, zero final-check violations. Independent selection was valid on 2 cases and duplicated a replacement on 2. |
| Human evaluation | Four joint cases await culinary grading. The onion–celery proposal awaits a reviewer. |
| Scheduling and hosting | The course deadline and team availability have not been supplied. A public hosting URL has not been recorded. The app runs locally for the demo. |

## Run and review

Use the PowerShell commands in [README.md](README.md), then open **Joint replacements**. The [demo guide](docs/DEMO_WINDOWS.md) includes examples with a feasible baseline, a duplicate baseline and an empty pantry.

The [Phase 4 notes](docs/PHASE_4.md), [callable examples](docs/SERVICE_CONTRACT_EXAMPLES.md), [benchmark report](results/development_joint_plans.json) and [verification record](results/verification.txt) describe the checkpoint. To regenerate it, follow the README development commands. The feature builder regenerates all development reports before recording SHA-256 hashes. Both original human review sheets are available under `data/benchmark/`. Leave the test split sealed.

To package a verified rebuild on Windows, run this in the extracted project folder.

```powershell
.\.venv\Scripts\python.exe scripts\package_handoff.py --phase 4 --output dist
```
