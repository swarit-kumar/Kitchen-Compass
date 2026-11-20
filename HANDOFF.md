# KitchenCompass handoff · Phase 3

| Item | Checkpoint |
|---|---|
| Plan | Shared Implementation and Handoff Plan 1.0, included in `docs/` |
| Snapshot | P03-v0.4.2-20261120 · ZIP handoff · ready_for_review |
| Sender / receiver | Vibhu / Swarit |
| Parent | Swarit’s `Kitchen-Compass-main.zip`, SHA-256 `2ecccff9be475984c9cf307e5891434f965addcc30a25a3308af56ca684c74c9` |
| Catalogue / config / benchmark | 2.0 / 0.4.0 / groups_seed_42_v2 |
| Schemas | Catalogue and result envelope 1.0. Custom recipe export 2.0 reads earlier 1.0 inputs. |
| Environment | Verified with CPython 3.11.18 on Linux x86-64 and the pinned requirements. Windows instructions in README. |
| Receiver verification | Pending Swarit’s clean extraction, Windows test run and rule review. |

### Changes since Swarit’s handoff

- Added a separately callable overlap baseline and corrected ranking to sort on full-precision scores. Both pantry methods use the same exclusions, including compound ingredients.
- Rebuilt the hashes against the distributed LF files and set an explicit Git line-ending rule. The earlier ZIP had seven CRLF/LF checksum mismatches.
- Added ingredient confirmation for custom entry and import. The original wording, quantity, essential flags, instructions and UUID survive export/import. Duplicate entries retain their original lines and at least two distinct IDs must resolve. The catalogue and training corpus are read-only during a session.
- Added a frozen catalogue loader and single-target service, instruction-based roles, molecular Jaccard, training-only context cosine, hard filters, optional purchases, ranked explanations and four comparison modes.
- Integrated the screens, four demo examples, development runner and regression tests. The per-case outputs and validation commands are included. Notes P2-01, P2-02, P3-01 and P3-02 are in the decision log.

### v0.4.2 update

Pantry search and substitutions show five ranked results initially and reveal up to five more per click. Each pantry result has a View recipe button for ingredients and instructions. A new search resets the visible count. The development benchmark retains its five-result budget.

### Verification

See `results/verification.txt` for the actual execution environment and checks. A clean unpack must pass `python -m pytest -q` before receiver acceptance. The expected count is 45 tests. The ZIP includes its dependencies list, data, prebuilt features, application, benchmark files, original plan and demo instructions. Virtual environments, build metadata and caches are omitted. Use the ZIP SHA-256 supplied with the download to check the transfer.

### Open items and next task

Swarit should first run [the Windows walkthrough](docs/DEMO_WINDOWS.md) and record the received ZIP digest, Python version, test result, date and acceptance decision here. Review the instruction and pair rules in [the implementation notes](docs/PHASE_3.md). Both teammates still need to independently grade the existing cases and reconcile their judgments. Five molecular profiles are available. Course deadline, weekly availability, professor approval of the benchmark scope and hosting smoke-test record are still unconfirmed.

The next implementation phase is constrained joint substitution for one to three targets. Its planned entry point is `kitchencompass/adapt.py`. The Phase 3 demo covers a single replacement. The previous [Phase 2 handoff](docs/history/PHASE_2_HANDOFF.md) is retained for provenance.
