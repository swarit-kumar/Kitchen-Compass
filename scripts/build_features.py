"""Build reproducible training-only context vectors and the data manifest."""
import argparse
from importlib.metadata import version
import platform

from kitchencompass.adapt import MAX_CANDIDATES_PER_TARGET, MAX_COMBINATIONS, MAX_TARGETS
from kitchencompass.catalog import Catalog
from kitchencompass.development import publish_reports
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

    joint, _ = publish_reports(Catalog(config_path=config_path))
    inputs = [
        config["raw_recipes"], config["curation"], config["flavor_snapshot"], config_path.as_posix(),
        "kitchencompass/schemas.py", "kitchencompass/data_io.py",
        "kitchencompass/prepare.py", "kitchencompass/context.py",
        "kitchencompass/normalize.py", "kitchencompass/constraints.py",
        "kitchencompass/recommend.py", "kitchencompass/service.py",
        "kitchencompass/custom_recipes.py", "app.py",
        "scripts/prepare_data.py", "scripts/build_features.py",
        "requirements.txt", "data/benchmark/dev_cases.jsonl",
        ".gitattributes", "kitchencompass/catalog.py", "kitchencompass/roles.py",
        "kitchencompass/features.py", "kitchencompass/substitute.py", "scripts/evaluate.py",
        "data/processed/substitution_pairs.jsonl", "data/curation/substitution_policy.json",
        "tests/test_substitute.py", "tests/test_custom_recipe.py", "tests/test_recommend.py",
        "tests/test_phase3_app.py", "tests/test_development.py",
        "kitchencompass/adapt.py", "kitchencompass/__init__.py", "kitchencompass/development.py",
        "kitchencompass/joint_evaluation.py", "data/processed/pair_compatibility.jsonl",
        "tests/test_adapt.py", "tests/test_joint_service.py", "scripts/check_joint_cases.py",
        "scripts/update_phase4_manifest.py", "scripts/package_handoff.py",
        "docs/SERVICE_CONTRACT_EXAMPLES.md", "docs/PHASE_4.md", "docs/DEMO_WINDOWS.md",
        "docs/BENCHMARK_GUIDE.md", "docs/DATA_SOURCES.md", "docs/DECISIONS.md", "docs/PHASE_2_START.md",
        "docs/PHASE_3.md", "docs/history/PHASE_1_VERIFICATION.txt", "docs/history/PHASE_2_HANDOFF.md",
        "docs/KitchenCompass_Shared_Implementation_and_Handoff_Plan.docx", "data/benchmark/review_swarit.md",
        "data/benchmark/review_vibhu.md", "data/benchmark/archive/v1/dev_cases.jsonl",
        "data/benchmark/archive/v1/splits.json", "README.md", "HANDOFF.md", ".gitignore",
        "requirements.in", "pyproject.toml", "results/verification.txt",
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
        "results/development_joint_plans.json", "results/development_pantry.json", "results/development_substitution.json",
    ]
    from kitchencompass.benchmark import BASE, REVIEWERS, verify_protocol
    if __package__:
        from .evaluate import publish
    else:
        from evaluate import publish
    verify_protocol()
    dev_report = publish("dev", config_path)
    inputs.extend([
        "kitchencompass/experiments.py", "kitchencompass/benchmark.py", "kitchencompass/annotations.py",
        "kitchencompass/experiment_metrics.py", "scripts/benchmark.py", "scripts/measure_runtime.py",
        "tests/test_phase5.py", "docs/EVALUATION.md", "docs/history/PHASE_4_HANDOFF.md",
        "data/benchmark/phase5/dev_cases.jsonl", "data/benchmark/phase5/test_cases.jsonl",
        "data/benchmark/phase5/protocol_lock.json", "data/benchmark/phase5/reviews/reconciliation.csv",
        *(f"data/benchmark/phase5/reviews/{name}.csv" for name in REVIEWERS),
    ])
    outputs.extend(["results/per_case.jsonl", "results/metrics.json", "results/summary.csv", "results/runtime.json"])
    if (BASE/"labels_lock.json").exists():
        inputs.append("data/benchmark/phase5/labels_lock.json")
        # Test scoring occurs only through the explicit final evaluation command.
        test_metrics = ROOT/"results/test/metrics.json"
        if test_metrics.exists():
            meta = read_json(test_metrics)
            if (meta["split"] != "test" or meta["labels_sha256"] != sha256(BASE/"labels_lock.json")
                    or meta["protocol_sha256"] != sha256(BASE/"protocol_lock.json")):
                raise ValueError("Test results disagree with the frozen label or protocol snapshot.")
            outputs.extend("results/test/" + name for name in ("metrics.json","per_case.jsonl","summary.csv"))
    write_json(ROOT / "artifacts/manifest.json", {
        "schema_version": config["schema_version"], "data_version": config["data_version"],
        "config_version": config["config_version"], "split_id": splits["split_id"], "seed": splits["seed"],
        "phase5": {"checkpoint": "P05-v0.6.0-20261123", "label_status": dev_report["label_status"],
                   "protocol_sha256": dev_report["protocol_sha256"], "development_cases": dev_report["cases"]},
        "phase4": {"checkpoint": "P04-v0.5.0-20261123", "max_targets": MAX_TARGETS,
                   "max_candidates_per_target": MAX_CANDIDATES_PER_TARGET, "max_combinations": MAX_COMBINATIONS,
                   "development_cases": len(joint["cases"]), "review_statuses": sorted({c["review_status"] for c in joint["cases"]})},
        "counts": {"recipes": len(recipes), "ingredients": len(ingredients), "train_recipes": context["n_training_recipes"]},
        "input_sha256": {path: sha256(ROOT / path) for path in inputs},
        "output_sha256": {path: sha256(ROOT / path) for path in outputs},
        "python_version": platform.python_version(),
        "package_versions": {name: version(name) for name in ("pydantic", "streamlit", "numpy", "pandas", "pytest")},
    })
    print(f"Context built from {context['n_training_recipes']} training recipes ({len(ingredients)} ingredient IDs)")


if __name__ == "__main__":
    main()
