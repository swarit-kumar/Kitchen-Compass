# Phase 1 data sources

## Recipe snapshots

The original 72-record KitchenCompass starter is preserved byte-for-byte in
`data/raw/KitchenCompass_Recipes_v1.json`. The v2 snapshot retains all of
its records and adds 176 recipe drafts across 44 preparation groups. The
expansion is AI-assisted and includes standardized versions and explicitly
named variants of Indian and international dishes. Recipes were created for
the project. Their instructions and quantities are drafts without independent
source validation or cooking trials. Their frequencies describe this authored
dataset. These recipe sources provide context for the coursework and do not
establish substitution quality.

`data/curation/recipe_expansion_v2.txt` contains the authored variants.
`scripts/expand_recipes.py --check` independently reconstructs the raw v2
snapshot and curation in memory and compares them against the packaged files.
Raw v2 records cite either the v1 snapshot or the authored expansion input.

All 248 records passed parsing. The soup and curry filter retained 224
candidates. Twelve candidates with unresolved compound ingredients are
excluded, leaving 212 eligible records with distinct canonical ingredient
sets. The 24 other dishes and excluded soup/curry records are still available
in the raw data. See the audit for the exact reasons. The 162 canonical
ingredient records include 152 direct recipe ingredients and 10 components
used for exclusion expansion. This exceeds the initial vocabulary estimate
of 100–150. Component IDs are kept to preserve the ingredient relationships.

The chicken, fish and shrimp doneness guidance in authored instructions
uses the [FoodSafety.gov safe minimum internal temperature chart](https://www.foodsafety.gov/food-safety-charts/safe-minimum-internal-temperatures).

## Project curation

`data/curation/catalogue.json` records the proposed canonical labels, aliases,
role defaults, instruction rules, essential ingredient annotations and explicit
component relations. Component entries describe the project's specified plain
versions or house formulations. Examples include a basic carrot, celery and
onion vegetable stock and pure sunflower oil for the generic vegetable oil
entry. For prepackaged products, confirm the ingredients against the actual
product before using a matching definition. Products with unresolved
components are kept outside the active catalogue. Component expansion is for
project exclusions and does not validate real-world allergen safety.

Spice formulations and role labels are project judgments. Both teammates
should review them. New data and changes to curation should be versioned.
The duplicate groups combine explicit recipe-family links with a normalized
ingredient-set Jaccard threshold of 0.85. Exact normalized record duplicates
are removed. Review the groups before accepting the split.

## FlavorDB evidence

The included `data/raw/flavordb_entity_cids.json` is a PubChem-ID projection
of the following IIIT-Delhi CoSyLab entity tables, retrieved 12 November 2026.

| Canonical ingredient | Source | Published table rows |
|---|---|---:|
| tomato | [FlavorDB2 Tomato](https://cosylab.iiitd.edu.in/flavordb2/entity_details?id=364) | 271 |
| potato | [FlavorDB2 Potato](https://cosylab.iiitd.edu.in/flavordb2/entity_details?id=373) | 254 |
| grated coconut | [FlavorDB2 Coconut](https://cosylab.iiitd.edu.in/flavordb2/entity_details?id=172) | 161 |
| garlic | [FlavorDB2 Garlic](https://cosylab.iiitd.edu.in/flavordb2/entity_details?id=259) | 143 |
| onion | [FlavorDB Onion](https://cosylab.iiitd.edu.in/flavordb/entity_details?id=348) | 180 |

The coconut profile is mapped to unsweetened grated coconut as the underlying
ingredient. A separate processed form receives no molecular evidence
automatically. The other 157 canonical ingredient profiles are explicitly
missing. This snapshot supports development and verification. It has limited
coverage for a flavor-only evaluation. The project makes no substitution
quality claim based on these profiles.

For additional profiles, use the
[FlavorDB2 ingredient search](https://cosylab.iiitd.edu.in/flavordb2/search).
Confirm the exact entity match, then use the entity page's download or PubChem
ID column. Save verified source URLs, date, locator and complete CID lists in
a new versioned snapshot, then rerun preparation. The snapshot included here
allows preparation to run offline. Its SHA-256 is in the audit and manifest.

Attribution: Neelansh Garg, Apuroop Sethupathy, Rudraksh Tuwani, and coauthors,
“FlavorDB: a database of flavor molecules,” Nucleic Acids Research,
DOI [10.1093/nar/gkx957](https://doi.org/10.1093/nar/gkx957).
The [FlavorDB FAQ](https://cosylab.iiitd.edu.in/flavordb/faq) and
[FlavorDB2 FAQ](https://cosylab.iiitd.edu.in/flavordb2/faq) describe the
[CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/) terms.
Apply these terms to the projected and processed FlavorDB data, retain this
attribution and confirm licensing before public release.
