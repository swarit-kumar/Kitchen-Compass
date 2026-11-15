# Phase 2 start for Swarit

Swarit leads Phase 2. Vibhu reviews it. Use the plan's Phase 2 section and
the v2 processed files. Preserve the raw snapshots and the v2 split. The
Streamlit app is currently the shell.

1. Add `normalize.py` and `constraints.py`. Resolve canonical IDs and
   aliases. Return explicit suggestions for uncertain names. Apply exclusions
   through nested component relationships. For example, excluding milk should
   exclude ghee through its butter component.
2. Add `recommend.py` and update the service layer. Compute baseline coverage
   as matched distinct ingredients divided by all distinct ingredients.
   Give essential ingredients weight 2 and others weight 1. The weighted
   score is `0.8 * weighted_coverage + 0.2 / (1 + missing_count)`.
   Sort by descending score, ascending missing count, then recipe ID.
   Return up to five recipes with their matches, missing items and an
   explanation. Exclusions are hard filters. Pantry-only mode applies to
   later substitution candidates, so discovery can show missing items.
3. Connect pantry entry, exclusions and results to Streamlit. Add explicit
   handling for an empty pantry, unresolved ingredient names and no results.
4. Add custom recipe input and validation. Use UUID-based recipe IDs,
   preserve original ingredient quantities and instruction order, keep the
   record in its session, and support schema-versioned JSON export/import.
5. Test an alias, a nested compound exclusion, an empty pantry, stable
   ranking ties, and a custom recipe round trip. Use the draft development
   scenarios and keep test groups out of tuning.

Suggested first demonstration: enter the pantry from `dev_v2_01` and
exclude milk. Check that Lemon Coriander Soup is eligible and Broccoli
Cheddar Soup is removed. The development sheets contain proposed candidates
and pending human grades.
