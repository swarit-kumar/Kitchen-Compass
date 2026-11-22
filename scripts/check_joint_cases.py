
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kitchencompass.adapt import (
    generate_candidate_lists,
    generate_joint_plans,
    generate_independent_baseline,
    validate_plan,
)
from kitchencompass.catalog import Catalog
from kitchencompass.schemas import Constraints


source = Path("results/development_substitution.json")
destination = Path("results/development_joint_plans.json")

data = json.loads(source.read_text(encoding="utf-8"))
catalog = Catalog()

output = {
    "schema_version": "1.0",
    "split": data.get("split"),
    "split_id": data.get("split_id"),
    "status": "development_pending_review",
    "quality_note": (
        "Development-only outputs generated from pending-review "
        "substitution evidence. Not validated culinary recommendations."
    ),
    "cases": [],
}

seen = set()

for case in data["cases"]:
    recipe = catalog.recipes[case["recipe_id"]]
    recipe_ids = [
        item["ingredient_id"]
        for item in recipe["ingredients"]
    ]
    constraints = Constraints(**case["constraints"])

    other_targets = [
        ingredient_id
        for ingredient_id in recipe_ids
        if ingredient_id != case["target_id"]
    ]

    for other_target in other_targets:
        targets = [case["target_id"], other_target]
        key = (case["case_id"], tuple(targets))

        if key in seen:
            continue
        seen.add(key)

        candidate_lists = generate_candidate_lists(
            recipe,
            targets,
            constraints,
            catalog,
        )

        if not all(candidate_lists.get(target) for target in targets):
            continue

        plans = generate_joint_plans(
            candidate_lists,
            catalog,
            recipe,
        )

        baseline = generate_independent_baseline(
            candidate_lists,
            targets,
            catalog,
            recipe,
        )

        validated_plans = []

        for plan in plans:
            validation = validate_plan(
                recipe,
                targets,
                plan,
                constraints,
                catalog,
            )

            validated_plans.append({
                "plan": plan,
                "validation": validation,
            })

        output["cases"].append({
            "case_id": case["case_id"],
            "recipe_id": case["recipe_id"],
            "target_ids": targets,
            "candidate_counts": {
                target: len(candidate_lists[target])
                for target in targets
            },
            "joint_plans": validated_plans,
            "independent_baseline": baseline,
            "review_status": "pending_review",
            "evidence_note": (
                "Candidate evidence is not manually reviewed; "
                "scores are software outputs, not culinary guarantees."
            ),
        })

destination.write_text(
    json.dumps(output, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

print("Saved:", destination)
print("Eligible cases:", len(output["cases"]))

for case in output["cases"]:
    valid_count = sum(
        item["validation"]["valid"]
        for item in case["joint_plans"]
    )
    print(
        case["case_id"],
        case["target_ids"],
        "joint plans:", len(case["joint_plans"]),
        "valid plans:", valid_count,
        "baseline valid:", case["independent_baseline"].get("valid"),
    )
