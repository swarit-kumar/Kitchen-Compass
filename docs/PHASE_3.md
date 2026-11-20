# Single-ingredient substitution

The app and development runner call `kitchencompass.service.rank_substitutes(recipe, target_id, constraints, top_k=5, mode="full")`. The recipe can be a catalogue ID, a validated catalogue record or a session-private CustomRecipe. Results carry schema 1.0, data 2.0 and config 0.4.0. The source of truth for weights and thresholds is `config/settings.json`.

## From recipe to candidates

1. Resolve every ingredient. Check that the target occurs in the recipe. Expand exclusions through the catalogue's component graph. An excluded target may be replaced. An excluded retained ingredient stops the request with `UNRESOLVED_EXCLUSION`.
2. Start with 162 canonical IDs. Remove the target, retained ingredients, exclusions and their derivatives. Intersect with pantry IDs when requested. Apply source-checked, instruction-specific pair blocks to every method. Each filtered ID counts once, under the first matching reason. An outside-pantry suggestion includes a purchase flag.
3. Match rules only in an instruction clause explicitly naming the target. Prefer an ingredient rule over a category rule, then higher priority. Tied conflicts expose both roles and a warning. If nothing matches, use catalogue roles. A custom recipe without instructions explains that fallback.
4. Score the surviving candidates, sort by the unrounded score then canonical ID, and show up to five initially. **Show 5 more** reveals further eligible results in order. Each result shows its evidence, active features, role basis and purchase status. Original instructions and quantities stay available.

## Scoring and comparisons

| Component | Calculation | When unavailable |
|---|---|---|
| F, flavor | Jaccard overlap of target and candidate PubChem compound sets. Disjoint measured profiles give zero. | Either profile is missing. |
| C, context | Cosine of the candidate's positive pointwise mutual information vector and the mean vector of distinct retained ingredients. | Either vector has zero norm. |
| R, role | Highest allowed match between target and candidate roles. Equal roles score 1. A source-checked, scoped partial match scores 0.5. Other known pairs score 0. | The target or candidate lacks a modelled role. |

The default weights for F, C and R are 0.35, 0.35 and 0.30. The full method needs R ≥ 0.5 and at least one measured F or C. It rescales weights over available components and requires a score ≥ 0.40. **Flavor only** ranks every measured F, including zero. **Without recipe context** uses F and R plus the role and score thresholds. **Without cooking roles** removes R and its gate and scores any available F or C with the 0.40 threshold. Hard filters apply throughout. The development benchmark uses the first five results.

Role rules in `data/processed/role_rules.json` come from Phase 1 project curation. The two new directed pair blocks cover a whole substitution of liquid oil for butter only when an instruction explicitly creams butter and sugar. An ingredient-specific partial role permits potato as a soup thickener and flags the need for cooking and mashing. These source checks are implementation judgments, pending Swarit’s independent review. The rules identify their evidence and reviewer in `data/processed/substitution_pairs.jsonl` and `data/curation/substitution_policy.json`. [Creaming method](https://www.kingarthurbaking.com/blog/2015/04/27/creaming-butter-and-sugar) · [Soup thickening example](https://extension.umd.edu/programs/family-consumer-sciences/snap-ed/eat-smart/recipes/broccoli-and-potato-soup)

## Development results

| Method | Cases with a result | Abstentions | Returned suggestions violating hard constraints |
|---|---:|---:|---:|
| Full | 6/6 | 0 | 0 |
| Flavor only | 0/6 | 6 | 0 |
| Without recipe context | 0/6 | 6 | 0 |
| Without cooking roles | 2/6 | 4 | 0 |

All six existing substitution cases were run with their original pantry, exclusions, recipe group and target. None had a candidate in its allowed pool with all three features measured. Compare each method on all cases and on the shared complete-evidence pool in [the per-case output](../results/development_substitution.json). An empty common pool has a denominator of zero. The [pantry output](../results/development_pantry.json) records both discovery methods on the five pantry cases. No test-set labels or cases were evaluated.

The two independent review sheets are still blank. Hit@3, reciprocal rank over the five returned positions, human top-three plausibility and candidate-generation recall therefore have null values. After reconciling grades, run the same development command. Each reconciled single-target case should supply one `candidate_judgments` record per option with `candidate_id` (e.g. `option_1`) and an integer `grade` (0–2), named annotators, and review status `reconciled`. Store rationales and evidence with the judgments. The runner counts eligible misses and abstentions as zero and leaves unknown grades unscored. Independent review remains with the team.

The short classroom examples in [the demo guide](DEMO_WINDOWS.md) can illustrate available flavor evidence, a triggered instruction rule and a justified empty result. Demonstration cases and synthetic software tests do not add benchmark judgments.
