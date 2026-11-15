"""Build reproducible training-only context vectors and the data manifest."""
import argparse
from importlib.metadata import version
import platform

from kitchencompass.context import build_context
from kitchencompass.data_io import ROOT, read_json, read_records, sha256, write_json
from kitchencompass.schemas import Ingredient, Recipe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/settings.json")
    args = parser.parse_args()
    config_path = (ROOT / args.config).resolve().relative_to(ROOT)
    config = read_json(ROOT / config_path)
    recipes = read_records(ROOT / "data/processed/recipes.jsonl", Recipe)
    ingredients = read_records(ROOT / "data/processed/ingredients.jsonl", Ingredient)
    splits = read_json(ROOT / "data/benchmark/splits.json")
    context = build_context(recipes, ingredients, splits)
    write_json(ROOT / "artifacts/context_vectors.json", context)

    inputs = [
        config["raw_recipes"], config["curation"], config["flavor_snapshot"], config_path.as_posix(),
        "kitchencompass/schemas.py", "kitchencompass/data_io.py",
        "kitchencompass/prepare.py", "kitchencompass/context.py",
        "kitchencompass/normalize.py", "kitchencompass/constraints.py",
        "kitchencompass/recommend.py", "kitchencompass/service.py",
        "kitchencompass/custom_recipes.py", "app.py",
        "scripts/prepare_data.py", "scripts/build_features.py",
        "requirements.txt", "data/benchmark/dev_cases.jsonl",
        "tests/test_contracts.py", "tests/test_phase1.py", "tests/test_phase2.py",
    ]
    if config["data_version"] == "2.0":
        inputs.extend([
            "data/raw/KitchenCompass_Recipes_v1.json", "data/curation/catalogue_v1.json",
            "data/curation/recipe_expansion_v2.txt", "scripts/expand_recipes.py",
        ])
    outputs = [
        "data/processed/recipes.jsonl", "data/processed/ingredients.jsonl", "data/processed/sources.jsonl",
        "data/processed/flavors.jsonl", "data/processed/role_rules.json", "data/benchmark/splits.json",
        "artifacts/context_vectors.json", "results/data_audit.json",
    ]
    write_json(ROOT / "artifacts/manifest.json", {
        "schema_version": config["schema_version"], "data_version": config["data_version"],
        "config_version": config["config_version"], "split_id": splits["split_id"], "seed": splits["seed"],
        "counts": {"recipes": len(recipes), "ingredients": len(ingredients), "train_recipes": context["n_training_recipes"]},
        "input_sha256": {path: sha256(ROOT / path) for path in inputs},
        "output_sha256": {path: sha256(ROOT / path) for path in outputs},
        "python_version": platform.python_version(),
        "package_versions": {name: version(name) for name in ("pydantic", "streamlit", "numpy", "pandas", "pytest")},
    })
    print(f"Context built from {context['n_training_recipes']} training recipes ({len(ingredients)} ingredient IDs)")


if __name__ == "__main__":
    main()
