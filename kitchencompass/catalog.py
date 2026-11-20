"""Read-only application catalogue and frozen model inputs."""
import json
from math import isfinite
from pathlib import Path

from .constraints import ConstraintEngine
from .context import validate_splits
from .data_io import ROOT, index_by, read_json, read_records
from .normalize import IngredientNormalizer
from .schemas import FlavorProfile, Ingredient, Recipe, RoleRule


def load_jsonl(path):
    with Path(path).open(encoding="utf-8-sig") as stream:
        return [json.loads(line) for line in stream if line.strip()]


class Catalog:
    def __init__(self, root=ROOT, config_path="config/settings.json"):
        root = Path(root)
        self.config = read_json(root / config_path)
        data = root / "data/processed"
        ingredients = read_records(data / "ingredients.jsonl", Ingredient)
        recipes = read_records(data / "recipes.jsonl", Recipe)
        self.ingredients = {key: item.model_dump() for key, item in index_by(ingredients, "ingredient_id").items()}
        self.recipes = {key: item.model_dump() for key, item in index_by(recipes, "recipe_id").items()}
        self.normalizer = IngredientNormalizer(self.ingredients.values())
        self.constraints = ConstraintEngine(self.ingredients.values())
        self.profiles = index_by(read_records(data / "flavors.jsonl", FlavorProfile), "ingredient_id")
        self.compounds = {key: set(profile.compound_ids) for key, profile in self.profiles.items()}
        self.rules = [RoleRule.model_validate(row).model_dump() for row in read_json(data / "role_rules.json")]
        self.policy = read_json(root / "data/curation/substitution_policy.json")
        self.pairs = load_jsonl(data / "substitution_pairs.jsonl")
        context = read_json(root / "artifacts/context_vectors.json")
        splits = read_json(root / "data/benchmark/splits.json")
        validate_splits(recipes, splits)
        self.split_id = splits["split_id"]
        self.vectors = context["vectors"]
        known = set(self.ingredients)
        if (context["split_id"] != self.split_id or context["training_recipe_ids"] != splits["recipes"]["train"]
                or set(context["vocabulary"]) != known or set(self.vectors) != known or set(self.compounds) != known):
            raise ValueError("Feature snapshot does not match the frozen vocabulary and training split.")
        if any(set(row) - known or any(not isfinite(v) or v < 0 for v in row.values()) for row in self.vectors.values()):
            raise ValueError("Invalid context vector.")
        for recipe in recipes:
            ids = {entry.ingredient_id for entry in recipe.ingredients}
            if len(ids) < 2 or ids - known:
                raise ValueError(f"Invalid ingredient IDs in {recipe.recipe_id}.")
        rule_ids = set()
        for rule in self.rules:
            if rule["rule_id"] in rule_ids or set(rule["ingredient_ids"]) - known:
                raise ValueError("Duplicate or unknown instruction role rule.")
            rule_ids.add(rule["rule_id"])
        for pair in self.pairs:
            if {pair["original_id"], pair["candidate_id"]} - known or not pair["evidence_ref"]:
                raise ValueError("Invalid substitution pair rule.")
        if any(set(rule["candidate_ids"]) - known for rule in self.policy["partial_matches"]):
            raise ValueError("Unknown ingredient in partial role match.")

    @property
    def versions(self):
        return {key: self.config[key] for key in ("schema_version", "data_version", "config_version")}
