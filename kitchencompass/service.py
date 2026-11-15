
"""Application service connecting normalization, constraints and ranking."""

import json
from pathlib import Path

from kitchencompass.normalize import IngredientNormalizer
from kitchencompass.constraints import ConstraintEngine
from kitchencompass.recommend import recommend_recipes
from kitchencompass.schemas import Result


def load_jsonl(path):
    """Read JSON Lines data without modifying the source file."""
    with Path(path).open(encoding="utf-8-sig") as file:
        return [
            json.loads(line)
            for line in file
            if line.strip()
        ]


def recommend_for_pantry(
    pantry_names,
    excluded_names=None,
    data_dir="data/processed",
    limit=5,
):
    """Resolve user inputs and return ranked recipe recommendations."""

    data_dir = Path(data_dir)
    excluded_names = excluded_names or []

    ingredients = load_jsonl(data_dir / "ingredients.jsonl")
    recipes = load_jsonl(data_dir / "recipes.jsonl")

    normalizer = IngredientNormalizer(ingredients)

    if not pantry_names:
        return Result(
            status="NEEDS_INPUT",
            warnings=["Please enter at least one pantry ingredient."],
        )

    pantry_ids = []
    for name in pantry_names:
        result = normalizer.resolve(name)

        if result["status"] != "RESOLVED":
            return Result(
                status="UNSUPPORTED_INPUT",
                warnings=[
                    f"Could not confidently resolve pantry ingredient "
                    f"'{name}'. Suggestions: {result['suggestions']}"
                ],
            )

        pantry_ids.append(result["ingredient_id"])

    excluded_ids = []
    for name in excluded_names:
        result = normalizer.resolve(name)

        if result["status"] != "RESOLVED":
            return Result(
                status="UNRESOLVED_EXCLUSION",
                warnings=[
                    f"Could not confidently resolve exclusion "
                    f"'{name}'. Suggestions: {result['suggestions']}"
                ],
            )

        excluded_ids.append(result["ingredient_id"])

    # Verify that every recipe ingredient ID exists in the catalogue.
    known_ids = {item["ingredient_id"] for item in ingredients}

    for recipe in recipes:
        for item in recipe["ingredients"]:
            if item["ingredient_id"] not in known_ids:
                return Result(
                    status="UNSUPPORTED_INPUT",
                    warnings=[
                        f"Recipe {recipe['recipe_id']} references unknown "
                        f"ingredient ID {item['ingredient_id']}."
                    ],
                )

    engine = ConstraintEngine(ingredients)
    eligible, expanded = engine.filter_recipes(recipes, excluded_ids)

    if not eligible:
        return Result(
            status="NO_FEASIBLE_RESULT",
            reason_counts={
                "excluded_by_constraints": len(recipes),
            },
            warnings=["No recipes satisfy the selected exclusions."],
        )

    result = recommend_recipes(
        recipes=recipes,
        ingredients=ingredients,
        pantry_ids=pantry_ids,
        excluded_ids=excluded_ids,
        limit=limit,
    )

    return Result(
        status="OK",
        items=result["items"],
        warnings=[
            "Exclusions applied: " + ", ".join(expanded)
        ] if expanded else [],
    )
