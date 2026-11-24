# Phase 4 joint replacement selection

The Streamlit **Joint replacements** screen and the development evaluator both call `kitchencompass.service.adapt_recipe`. The input can be a catalogue recipe ID, a validated recipe record or a session recipe with confirmed ingredient IDs.

## Selection and validation

1. Choose one to three distinct target IDs. The service checks the request-specific replacement limit and expands exclusions through ingredient components. If an excluded ingredient would remain in the dish, it identifies the conflict.
2. For each target, rank up to five candidates using the Phase 3 full model. Identify instruction roles in the original recipe. Calculate recipe context from the ingredients left after removing **all** targets. Apply pantry constraints, exclusions and preparation-specific substitution blocks before taking the five.
3. Enumerate the product of these lists, up to 125 combinations. Q is the mean individual score. J is the mean compatibility across replacement pairs. Score a multi-target plan as `0.8 × Q + 0.2 × J`. For one target use Q alone.
4. Reviewed pair rules take precedence over vector cosine in matching target-role contexts. A block wins. If several positive rules match different roles, use the lower score. Without a rule, use training-context cosine. A missing vector contributes 0 and an explicit warning. A measured cosine of 0 carries no missing-evidence warning.
5. Reconstruct each final recipe independently. Check exact coverage, distinct replacements, original and retained ingredient IDs, exclusions, pantry-only eligibility, maximum replacements, directed preparation blocks and replacement-pair blocks. Multiple original lines using the same ingredient share one substitution decision. Quantities and instruction text remain available in the original recipe.
6. Return at most three valid plans. Break score ties by fewer replacement purchases and then by the tuple of replacement IDs in target order. The independent comparator uses the highest-scoring candidate in each identical list, breaking ties by ID. Its output retains any duplicate or blocked selection.

## Development evidence

The four pre-existing joint cases in the frozen development split supplied the targets, pantry and exclusions. The evaluator records each case even if it returns zero plans. The independent selections and the joint output are in [the per-case report](../results/development_joint_plans.json).

| Case | Recipe | Targets | Valid plans returned | Independent choices |
|---|---|---:|---:|---|
| dev_v2_12 | Broccoli Cheddar Soup | 3 | 3 | Olive oil selected twice |
| dev_v2_13 | New England Style Fish Chowder | 2 | 3 | Olive oil selected twice |
| dev_v2_14 | Black Pepper Paneer | 2 | 2 | Valid |
| dev_v2_15 | Italian Tomato Basil Soup | 2 | 3 | Valid |

All 11 returned plans passed validation. The two feasible independent selections tied the top joint score. All four cases await human grading. An oil suggestion can meet encoded roles and exclusions while still giving a poor result in a chowder. A grade-2 hit rate requires human judgments about the resulting dish. The tests include a constructed hard-block interaction and an independent numerical enumeration of a 125-combination request.

## Pair evidence

`data/processed/pair_compatibility.jsonl` stores sorted distinct IDs, target roles, a score, a block flag, source, reviewer and review status. A reviewed row requires a named reviewer. The file includes a **pending** onion–celery aromatic proposal. Escoffier describes their use in mirepoix. The proposed numeric score is a project judgment awaiting review. Pending rows cannot change a recommendation. The current release uses the cosine fallback for all production replacement pairs. Source [Escoffier, French culinary techniques](https://www.escoffier.edu/blog/value-of-culinary-education/french-culinary-education-french-cooking-techniques-chefs-need-to-know/).

Swarit and Vibhu can use the existing [benchmark guide](BENCHMARK_GUIDE.md) and review sheets to grade the options independently. A grade requires the actual recipe context. For an unjudged returned plan the quality metric stays empty.
