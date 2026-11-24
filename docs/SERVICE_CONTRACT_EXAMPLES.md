# Public service examples

Run these examples in Python with the project installed. A result has `status`, `items`, `warnings`, `reason_counts`, and schema, data and config versions.

```python
from kitchencompass.schemas import Constraints
from kitchencompass.service import adapt_recipe, rank_substitutes, recommend_recipes

pantry = recommend_recipes(["ing_potato", "ing_onion"], Constraints())
single = rank_substitutes("rec_black_pepper_paneer", "ing_paneer", Constraints())
recipe = "rec_black_pepper_paneer"
targets = ["ing_paneer", "ing_red_bell_pepper"]
constraints = Constraints(
    pantry_ids=["ing_firm_tofu", "ing_silken_tofu", "ing_green_bell_pepper"],
    excluded_ids=["ing_milk"],
    pantry_only=True,
)
audit = {}
result = adapt_recipe(recipe, targets, constraints, top_k=3, audit=audit)
assert result.status == "OK"
plan = result.items[0]
assert plan["replacements"] == {
    "ing_paneer": "ing_firm_tofu",
    "ing_red_bell_pepper": "ing_green_bell_pepper",
}
assert plan["constraint_checks"]["valid"] and not plan["purchase_ids"]
print(plan["final_ids"], plan["score"], plan["component_scores"])
print(audit["baseline"]["valid"], audit["baseline"]["replacement_ids"])
```

| Example | Expected status | Reason |
|---|---|---|
| `adapt_recipe(recipe, [], constraints)` | NEEDS_INPUT | Select a target. |
| `adapt_recipe(recipe, targets + targets, constraints)` | UNSUPPORTED_INPUT | Too many or repeated targets. |
| `adapt_recipe(recipe, ["ing_red_bell_pepper"], constraints)` | UNRESOLVED_EXCLUSION | Retained paneer contains excluded milk. |
| `adapt_recipe(recipe, targets, Constraints(pantry_only=True))` | NO_FEASIBLE_RESULT | The allowed pantry is empty. |

Unsuccessful requests return an empty list and an explanation. For a completed search, the optional audit contains the five-or-fewer candidate IDs for each target, the number of combinations and the independent selection from those lists. A feasible baseline exposes its individual mean as `score` and its comparable joint objective as `joint_score`. An infeasible baseline keeps its selected IDs and reasons. A request rejected before candidate generation has no baseline.

The same function accepts a confirmed `CustomRecipe`. Plan mappings apply to the original ingredient lines in order, including repeated uses of the same ingredient. The original quantities and instructions remain with the recipe.
