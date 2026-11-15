"""Training-only PPMI context features for canonical ingredient IDs."""
from collections import Counter
from itertools import combinations
from math import log

from .data_io import index_by


def validate_splits(recipes, split):
    if set(split["recipes"]) != {"train", "dev", "test"} or set(split["groups"]) != {"train", "dev", "test"}:
        raise ValueError("Exactly train, dev and test buckets are required")
    by_id = index_by(recipes, "recipe_id")
    all_ids = set()
    all_groups = set()
    for name in ("train", "dev", "test"):
        ids = split["recipes"][name]
        groups = split["groups"][name]
        if not ids or len(set(ids)) != len(ids) or len(set(groups)) != len(groups):
            raise ValueError(f"Invalid or empty split {name}")
        if all_ids.intersection(ids) or all_groups.intersection(groups):
            raise ValueError("Recipe or duplicate group crosses splits")
        if not set(ids).issubset(by_id) or {by_id[rid].duplicate_group_id for rid in ids} != set(groups):
            raise ValueError(f"Unknown recipe or incorrect group assignment in {name}")
        all_ids.update(ids)
        all_groups.update(groups)
    if all_ids != set(by_id):
        raise ValueError("Splits do not cover the active catalogue")
    return by_id


def build_context(recipes, ingredients, split):
    by_recipe = validate_splits(recipes, split)
    vocabulary = sorted(index_by(ingredients, "ingredient_id"))
    known_ids = set(vocabulary)
    for recipe in recipes:
        for entry in recipe.ingredients:
            if entry.ingredient_id not in known_ids:
                raise ValueError(f"Unknown ingredient {entry.ingredient_id} in {recipe.recipe_id}")
    n_recipes = len(split["recipes"]["train"])
    occurrences = Counter()
    pairs = Counter()
    for recipe_id in split["recipes"]["train"]:
        ingredient_set = sorted({entry.ingredient_id for entry in by_recipe[recipe_id].ingredients})
        occurrences.update(ingredient_set)
        pairs.update(combinations(ingredient_set, 2))

    vectors = {key: {} for key in vocabulary}
    for (first, second), count in sorted(pairs.items()):
        value = round(max(0.0, log(n_recipes * count / (occurrences[first] * occurrences[second]))), 12)
        if value > 0:
            vectors[first][second] = value
            vectors[second][first] = value
    return {
        "split_id": split["split_id"],
        "method": "ppmi_natural_log",
        "training_recipe_ids": split["recipes"]["train"],
        "n_training_recipes": n_recipes,
        "vocabulary": vocabulary,
        "recipe_occurrence_counts": {key: occurrences[key] for key in vocabulary},
        "vectors": vectors,
    }
