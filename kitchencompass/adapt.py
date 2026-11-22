
"""Joint recipe adaptation using constrained ingredient substitutions."""

from itertools import combinations, product

from .schemas import Result


MAX_TARGETS = 3
MAX_CANDIDATES_PER_TARGET = 5
MAX_COMBINATIONS = 125


def validate_targets(recipe, target_ids, catalog):
    """Validate the requested ingredient targets before generating plans."""
    
    if not isinstance(target_ids, (list, tuple)):
        return Result(
            status="UNSUPPORTED_INPUT",
            items=[],
            schema_version="1.0",
        )

    if not target_ids:
        return Result(
            status="NEEDS_INPUT",
            items=[],
            schema_version="1.0",
        )
    
    
    
    if any(
        not isinstance(target_id, str) or not target_id.strip()
        for target_id in target_ids
    ):
        return Result(
            status="UNSUPPORTED_INPUT",
            items=[],
            schema_version="1.0",
        )
    
    
    

    if len(target_ids) > MAX_TARGETS:
        return Result(
            status="UNSUPPORTED_INPUT",
            items=[],
            schema_version="1.0",
        )

    if len(set(target_ids)) != len(target_ids):
        return Result(
            status="UNSUPPORTED_INPUT",
            items=[],
            schema_version="1.0",
        )

    recipe_ids = {
        item["ingredient_id"]
        for item in recipe["ingredients"]
    }

    if any(target_id not in recipe_ids for target_id in target_ids):
        return Result(
            status="NEEDS_INPUT",
            items=[],
            schema_version="1.0",
        )

    if any(target_id not in catalog.ingredients for target_id in target_ids):
        return Result(
            status="UNSUPPORTED_INPUT",
            items=[],
            schema_version="1.0",
        )

    return None



def generate_candidate_lists(
    recipe,
    target_ids,
    constraints,
    catalog,
    mode="full",
):
    """Generate up to five eligible candidates for each target."""

    from .substitute import rank

    target_set = set(target_ids)
    candidate_lists = {}

    retained_ingredients = [
        item
        for item in recipe["ingredients"]
        if item["ingredient_id"] not in target_set
    ]

    for target_id in target_ids:
        working_recipe = dict(recipe)
        working_recipe["ingredients"] = (
            retained_ingredients
            + [
                item
                for item in recipe["ingredients"]
                if item["ingredient_id"] == target_id
            ]
        )

        result = rank(
            catalog=catalog,
            recipe=working_recipe,
            target_id=target_id,
            constraints=constraints,
            top_k=None,
            mode=mode,
        )

        if result.status != "OK":
            candidate_lists[target_id] = []
            continue

        if not isinstance(result.items, list):
            candidate_lists[target_id] = []
            continue

        candidates = [
            candidate
            for candidate in result.items
            if candidate["candidate_id"] not in target_set
        ]

        candidate_lists[target_id] = candidates[
            :MAX_CANDIDATES_PER_TARGET
        ]

    return candidate_lists





def target_role_context(recipe, target_id, catalog):
    """Infer the recipe-specific roles of an original target ingredient."""

    from .roles import target_clauses, infer_roles

    target = catalog.ingredients[target_id]

    clauses = target_clauses(
        recipe,
        target_id,
        catalog.ingredients,
        catalog.policy["shorthand"],
    )

    role = infer_roles(target, catalog.rules, clauses)

    return {
        "roles": set(role["roles"]),
        "warnings": list(role["warnings"]),
    }



def pair_compatibility_score(
    first_id,
    second_id,
    catalog,
    context_roles=None,
):
    """Return pair compatibility using matching recipe-context evidence."""

    from .features import cosine

    ingredient_a, ingredient_b = sorted((first_id, second_id))
    context_roles = set(context_roles or [])

    matching_rules = [
        rule
        for rule in getattr(catalog, "pair_compatibility", [])
        if (
            rule.get("ingredient_a") == ingredient_a
            and rule.get("ingredient_b") == ingredient_b
            and context_roles.intersection(rule.get("context_roles", []))
        )
    ]

    # A matching hard block always takes priority.
    blocked_rule = next(
        (rule for rule in matching_rules if rule.get("blocked")),
        None,
    )

    if blocked_rule is not None:
        return {
            "score": None,
            "blocked": True,
            "source": "reviewed_pair_rule",
            "warning": None,
        }

    if matching_rules:
        rule = matching_rules[0]
        return {
            "score": rule["score"],
            "blocked": False,
            "source": "reviewed_pair_rule",
            "warning": None,
        }

    # No matching reviewed rule: use context-vector cosine.
    first_vector = catalog.vectors.get(first_id, {})
    second_vector = catalog.vectors.get(second_id, {})

    score = cosine(first_vector, second_vector)

    if score is None:
        return {
            "score": 0.0,
            "blocked": False,
            "source": "context_cosine",
            "warning": (
                f"Compatibility evidence unavailable for "
                f"{ingredient_a} and {ingredient_b}."
            ),
        }

    return {
        "score": score,
        "blocked": False,
        "source": "context_cosine",
        "warning": None,
    }







def score_joint_plan(selected_candidates, catalog, recipe, target_ids):
    """Score a joint plan using substitution quality and pair compatibility."""

    from itertools import combinations
    from math import fsum, isfinite

    def invalid_result(reason):
        return {
            "valid": False,
            "score": None,
            "reason": reason,
            "pair_details": [],
            "warnings": [],
        }

    if (
        not selected_candidates
        or len(selected_candidates) != len(target_ids)
    ):
        return invalid_result(
            "Invalid or empty candidate selection."
        )

    if len(set(target_ids)) != len(target_ids):
        return invalid_result(
            "Duplicate target IDs."
        )

    if len(target_ids) > MAX_TARGETS:
        return invalid_result(
            "At most three replacement targets are allowed."
        )

    if any(not isinstance(candidate, dict) for candidate in selected_candidates):
        return invalid_result(
            "Candidate records must be dictionaries."
        )

    if any(
        "candidate_id" not in candidate or "score" not in candidate
        for candidate in selected_candidates
    ):
        return invalid_result(
            "A candidate is missing its ID or score."
        )

    replacement_ids = [
        candidate["candidate_id"]
        for candidate in selected_candidates
    ]

    if any(
        not isinstance(ingredient_id, str) or not ingredient_id
        for ingredient_id in replacement_ids
    ):
        return invalid_result(
            "A candidate has an invalid ingredient ID."
        )

    if len(set(replacement_ids)) != len(replacement_ids):
        return invalid_result(
            "Duplicate replacement ingredient IDs."
        )

    if set(replacement_ids).intersection(target_ids):
        return invalid_result(
            "A target ingredient cannot be its own replacement."
        )

    candidate_scores = [
        candidate["score"]
        for candidate in selected_candidates
    ]

    if any(
        not isinstance(score, (int, float))
        or isinstance(score, bool)
        or not isfinite(score)
        or not 0 <= score <= 1
        for score in candidate_scores
    ):
        return invalid_result(
            "Candidate scores must be finite numbers between 0 and 1."
        )

    q_score = fsum(candidate_scores) / len(candidate_scores)

    # Infer context roles for the original ingredients being replaced.
    target_contexts = [
        target_role_context(recipe, target_id, catalog)
        for target_id in target_ids
    ]

    warnings = [
        warning
        for context in target_contexts
        for warning in context["warnings"]
    ]

    pair_scores = []
    pair_details = []

    for (first_index, first_id), (second_index, second_id) in combinations(
        enumerate(replacement_ids), 2
    ):
        context_roles = (
            target_contexts[first_index]["roles"]
            | target_contexts[second_index]["roles"]
        )

        compatibility = pair_compatibility_score(
            first_id,
            second_id,
            catalog,
            context_roles,
        )

        if compatibility["blocked"]:
            return {
                "valid": False,
                "score": None,
                "reason": "A replacement pair is blocked.",
                "pair_details": pair_details,
                "warnings": warnings,
            }

        pair_scores.append(compatibility["score"])

        pair_details.append({
            "ingredient_a": min(first_id, second_id),
            "ingredient_b": max(first_id, second_id),
            "score": compatibility["score"],
            "source": compatibility["source"],
            "context_roles": sorted(context_roles),
        })

        if compatibility["warning"]:
            warnings.append(compatibility["warning"])

    if not pair_scores:
        final_score = q_score
        j_score = None
    else:
        j_score = fsum(pair_scores) / len(pair_scores)
        final_score = 0.8 * q_score + 0.2 * j_score

    return {
        "valid": True,
        "score": final_score,
        "component_scores": {
            "Q": q_score,
            "J": j_score,
        },
        "pair_details": pair_details,
        "warnings": warnings,
    }
   
   
    


def generate_joint_plans(candidate_lists, catalog, recipe):
    """Generate and rank valid combinations of replacement candidates."""

    from itertools import product

    target_ids = list(candidate_lists)

    # Reject more than three replacement targets.
    if len(target_ids) > MAX_TARGETS:
        return []

    if not target_ids or any(
        not candidate_lists[target_id]
        for target_id in target_ids
    ):
        return []

    plans = []

    candidate_groups = [
        candidate_lists[target_id][:MAX_CANDIDATES_PER_TARGET]
        for target_id in target_ids
    ]
    
    # Reject malformed candidate records before combination generation.
    for group in candidate_groups:
        for candidate in group:
            if (
                not isinstance(candidate, dict)
                or not isinstance(candidate.get("candidate_id"), str)
                or not candidate["candidate_id"]
                or not isinstance(candidate.get("score"), (int, float))
                or isinstance(candidate.get("score"), bool)
            ):
                return []
    
    combination_count = 1

    for group in candidate_groups:
        combination_count *= len(group)

    if combination_count > MAX_COMBINATIONS:
        return []

    for selected in product(*candidate_groups):
        replacement_ids = tuple(
            candidate["candidate_id"]
            for candidate in selected
        )

        # A replacement cannot be duplicated.
        if len(set(replacement_ids)) != len(replacement_ids):
            continue

        # A target cannot replace another target.
        if set(replacement_ids).intersection(target_ids):
            continue

        scored = score_joint_plan(
            selected,
            catalog,
            recipe,
            target_ids,
        )

        if not scored["valid"]:
            continue

        purchase_count = sum(
            bool(candidate.get("purchase_required", False))
            for candidate in selected
        )

        plans.append({
            "target_ids": target_ids,
            "replacement_ids": list(replacement_ids),
            "score": scored["score"],
            "component_scores": scored["component_scores"],
            "pair_details": scored["pair_details"],
            "warnings": scored["warnings"],
            "purchase_count": purchase_count,
        })

    plans.sort(
        key=lambda plan: (
            -plan["score"],
            plan["purchase_count"],
            tuple(plan["replacement_ids"]),
        )
    )

    return plans






def generate_independent_baseline(
    candidate_lists,
    target_ids=None,
    catalog=None,
    recipe=None,
):
    """Select the individually highest-scoring candidate for each target.

    This baseline deliberately does not repair duplicate replacements
    or incompatible pairs. Those violations are reported for comparison.
    """

    target_ids = list(target_ids or candidate_lists)
    if len(target_ids) > MAX_TARGETS:
        return {
            "target_ids": target_ids,
            "replacement_ids": [],
            "score": None,
            "violations": [
                "At most three replacement targets are allowed."
            ],
            "valid": False,
        }

    if not target_ids:
        return {
            "target_ids": [],
            "replacement_ids": [],
            "score": None,
            "violations": ["No replacement targets supplied."],
        }

    selected = []

    for target_id in target_ids:
        candidates = candidate_lists.get(target_id, [])

        if not candidates:
            return {
                "target_ids": target_ids,
                "replacement_ids": [],
                "score": None,
                "violations": [
                    f"No candidates available for target {target_id}."
                ],
            }
            
        from math import isfinite

        for candidate in candidates[:MAX_CANDIDATES_PER_TARGET]:
            if not isinstance(candidate, dict):
                return {
                    "target_ids": target_ids,
                    "replacement_ids": [],
                    "score": None,
                    "violations": [
                        f"Invalid candidate record for target {target_id}."
                    ],
                    "valid": False,
                }

            candidate_id = candidate.get("candidate_id")
            score = candidate.get("score")

            if not isinstance(candidate_id, str) or not candidate_id:
                return {
                    "target_ids": target_ids,
                    "replacement_ids": [],
                    "score": None,
                    "violations": [
                        f"Invalid candidate ID for target {target_id}."
                    ],
                    "valid": False,
                }

            if (
                not isinstance(score, (int, float))
                or isinstance(score, bool)
                or not isfinite(score)
                or not 0 <= score <= 1
            ):
                return {
                    "target_ids": target_ids,
                    "replacement_ids": [],
                    "score": None,
                    "violations": [
                        f"Invalid candidate score for target {target_id}."
                    ],
                    "valid": False,
                }

        # Highest individual score; lexicographic ID breaks ties.
        best = min(
            candidates[:MAX_CANDIDATES_PER_TARGET],
            key=lambda candidate: (
                -candidate["score"],
                candidate["candidate_id"],
            ),
        )

        selected.append(best)

    replacement_ids = [
        candidate["candidate_id"]
        for candidate in selected
    ]

    violations = []

    if len(set(replacement_ids)) != len(replacement_ids):
        violations.append("Duplicate replacement IDs selected.")

    if set(replacement_ids).intersection(target_ids):
        violations.append("A target ingredient was selected as a replacement.")
        
        # Check reviewed hard-blocked pairs when context is supplied.
    if (catalog is None) != (recipe is None):
        violations.append(
            "Both catalog and recipe are required for pair validation."
        )

    elif catalog is not None:
        target_contexts = {
            target_id: target_role_context(
                recipe, target_id, catalog
            )
            for target_id in target_ids
        }

        for first_index, second_index in combinations(
            range(len(replacement_ids)), 2
        ):
            first_target = target_ids[first_index]
            second_target = target_ids[second_index]

            context_roles = (
                target_contexts[first_target]["roles"]
                | target_contexts[second_target]["roles"]
            )

            pair = pair_compatibility_score(
                replacement_ids[first_index],
                replacement_ids[second_index],
                catalog,
                context_roles,
            )

            if pair["blocked"]:
                violations.append(
                    "Blocked replacement pair: "
                    f"{replacement_ids[first_index]}, "
                    f"{replacement_ids[second_index]}."
                )

    return {
        "target_ids": target_ids,
        "replacement_ids": replacement_ids,
        "individual_scores": [
            candidate["score"] for candidate in selected
        ],
        "score": (
            sum(candidate["score"] for candidate in selected)
            / len(selected)
        ),
        "violations": violations,
        "valid": not violations,
    }



def validate_plan(recipe, target_ids, plan, constraints, catalog):
    """Independently validate a generated joint adaptation plan."""

    errors = []

    def invalid(message):
        return {
            "valid": False,
            "errors": [message],
            "final_ingredient_ids": [],
        }

    if not isinstance(plan, dict):
        return invalid("Plan must be a dictionary.")

    if not isinstance(target_ids, (list, tuple)) or not target_ids:
        return invalid("At least one replacement target is required.")

    target_ids = list(target_ids)

    if any(not isinstance(x, str) or not x.strip() for x in target_ids):
        return invalid("Target IDs must be non-empty strings.")

    if len(target_ids) > MAX_TARGETS:
        errors.append("At most three replacement targets are allowed.")

    if len(set(target_ids)) != len(target_ids):
        errors.append("Duplicate requested target IDs.")

    plan_targets = plan.get("target_ids", [])
    replacement_ids = plan.get("replacement_ids", [])

    if not isinstance(plan_targets, list):
        return invalid("Plan target IDs must be a list.")

    if not isinstance(replacement_ids, list):
        return invalid("Replacement IDs must be a list.")

    if any(not isinstance(x, str) or not x.strip() for x in plan_targets):
        return invalid("Plan target IDs must be non-empty strings.")

    if any(not isinstance(x, str) or not x.strip() for x in replacement_ids):
        return invalid("Replacement IDs must be non-empty strings.")

    if (
        len(plan_targets) != len(target_ids)
        or len(set(plan_targets)) != len(plan_targets)
        or set(plan_targets) != set(target_ids)
    ):
        errors.append("Requested targets are not covered exactly once.")

    if len(replacement_ids) != len(target_ids):
        errors.append("Replacement count does not match target count.")

    if len(set(replacement_ids)) != len(replacement_ids):
        errors.append("Duplicate replacement ingredients.")

    for ingredient_id in replacement_ids:
        if ingredient_id not in catalog.ingredients:
            errors.append(f"Unknown replacement ingredient: {ingredient_id}.")

    for target_id in target_ids:
        if target_id not in catalog.ingredients:
            errors.append(f"Unknown target ingredient: {target_id}.")

    if not isinstance(recipe, dict) or not isinstance(recipe.get("ingredients"), list):
        return invalid("Recipe must contain an ingredient list.")

    recipe_ids = []
    for item in recipe["ingredients"]:
        if not isinstance(item, dict):
            return invalid("Recipe contains a malformed ingredient entry.")
        ingredient_id = item.get("ingredient_id")
        if not isinstance(ingredient_id, str) or not ingredient_id.strip():
            return invalid("Recipe contains an invalid ingredient ID.")
        recipe_ids.append(ingredient_id)

    for ingredient_id in recipe_ids:
        if ingredient_id not in catalog.ingredients:
            errors.append(f"Unknown ingredient in original recipe: {ingredient_id}.")

    for target_id in target_ids:
        if recipe_ids.count(target_id) != 1:
            errors.append(f"Target {target_id} must occur exactly once in the recipe.")

    mapping_is_safe = (
        len(plan_targets) == len(replacement_ids)
        and len(set(plan_targets)) == len(plan_targets)
        and set(plan_targets) == set(target_ids)
    )

    final_ids = []
    if mapping_is_safe:
        replacements_by_target = dict(zip(plan_targets, replacement_ids))
        for ingredient_id in recipe_ids:
            final_ids.append(
                replacements_by_target.get(ingredient_id, ingredient_id)
            )

    retained_ids = set(recipe_ids) - set(target_ids)
    if set(replacement_ids) & retained_ids:
        errors.append("A replacement duplicates a retained ingredient.")

    if set(replacement_ids) & set(target_ids):
        errors.append("A target ingredient was selected as a replacement.")

    excluded_ids = set(
        catalog.constraints.expand_exclusions(constraints.excluded_ids)
    )
    if set(final_ids) & excluded_ids:
        errors.append("Final recipe contains an excluded ingredient.")

    if constraints.pantry_only:
        pantry_ids = set(constraints.pantry_ids)
        if not set(replacement_ids).issubset(pantry_ids):
            errors.append("A replacement is outside the available pantry.")

    if len(replacement_ids) > constraints.max_replacements:
        errors.append("Replacement count exceeds the allowed limit.")

    if mapping_is_safe and all(
        target_id in catalog.ingredients for target_id in target_ids
    ):
        target_contexts = {
            target_id: target_role_context(recipe, target_id, catalog)
            for target_id in target_ids
        }

        for first_index, second_index in combinations(
            range(len(replacement_ids)), 2
        ):
            first_id = replacement_ids[first_index]
            second_id = replacement_ids[second_index]

            if (
                first_id not in catalog.ingredients
                or second_id not in catalog.ingredients
            ):
                continue

            first_target = plan_targets[first_index]
            second_target = plan_targets[second_index]
            context_roles = (
                target_contexts[first_target]["roles"]
                | target_contexts[second_target]["roles"]
            )

            pair = pair_compatibility_score(
                first_id, second_id, catalog, context_roles
            )
            if pair["blocked"]:
                errors.append(f"Blocked replacement pair: {first_id}, {second_id}.")

    return {
        "valid": not errors,
        "errors": errors,
        "final_ingredient_ids": final_ids,
    }


