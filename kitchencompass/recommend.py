
"""Pantry-based recipe recommendation and ranking."""

from kitchencompass.constraints import ConstraintEngine


def recommend_recipes(
    recipes,
    ingredients,
    pantry_ids,
    excluded_ids=None,
    limit=5,
):
    """Rank recipes using pantry coverage and essential ingredient weights."""

    if limit < 1:
        raise ValueError("limit must be at least 1")

    excluded_ids = excluded_ids or []
    pantry = set(pantry_ids)

    ingredient_names = {
        item["ingredient_id"]: item["display_name"]
        for item in ingredients
    }

    constraints = ConstraintEngine(ingredients)

    eligible_recipes, expanded_exclusions = (
        constraints.filter_recipes(recipes, excluded_ids)
    )

    ranked = []

    for recipe in eligible_recipes:
        # Repeated entries of an ingredient count only once.
        essential_by_id = {}

        for item in recipe["ingredients"]:
            ingredient_id = item["ingredient_id"]
            essential_by_id[ingredient_id] = (
                essential_by_id.get(ingredient_id, False)
                or item["essential"]
            )

        all_ids = set(essential_by_id)
        matched_ids = all_ids & pantry
        missing_ids = all_ids - pantry

        total_weight = sum(
            2 if essential_by_id[i] else 1
            for i in all_ids
        )

        matched_weight = sum(
            2 if essential_by_id[i] else 1
            for i in matched_ids
        )

        coverage = (
            len(matched_ids) / len(all_ids)
            if all_ids else 0.0
        )

        weighted_coverage = (
            matched_weight / total_weight
            if total_weight else 0.0
        )

        missing_count = len(missing_ids)

        score = (
            0.8 * weighted_coverage
            + 0.2 / (1 + missing_count)
        )

        ranked.append({
            "recipe_id": recipe["recipe_id"],
            "title": recipe["title"],
            "score": round(score, 6),
            "coverage": round(coverage, 6),
            "weighted_coverage": round(weighted_coverage, 6),
            "missing_count": missing_count,
            "matches": [
                {
                    "ingredient_id": i,
                    "name": ingredient_names.get(i, i),
                }
                for i in sorted(matched_ids)
            ],
            "missing": [
                {
                    "ingredient_id": i,
                    "name": ingredient_names.get(i, i),
                    "essential": essential_by_id[i],
                }
                for i in sorted(missing_ids)
            ],
            "explanation": (
                f"{len(matched_ids)} of {len(all_ids)} distinct "
                f"ingredients available; {missing_count} missing."
            ),
        })

    # Deterministic ranking and tie-breaking.
    ranked.sort(
        key=lambda item: (
            -item["score"],
            item["missing_count"],
            item["recipe_id"],
        )
    )

    return {
        "items": ranked[:limit],
        "expanded_exclusions": expanded_exclusions,
        "eligible_recipe_count": len(eligible_recipes),
    }
