"""Joint recipe adaptation using constrained ingredient substitutions."""

from itertools import combinations, product

from .schemas import Result


MAX_TARGETS = 3
MAX_CANDIDATES_PER_TARGET = 5
MAX_COMBINATIONS = 125


def validate_targets(recipe, target_ids, catalog):
    def failure(status, warning):
        return Result(status=status, warnings=[warning], **getattr(catalog, "versions", {}))

    if not isinstance(target_ids, (list, tuple)) or any(
        not isinstance(key, str) or not key.strip() for key in target_ids
    ):
        return failure("UNSUPPORTED_INPUT", "Supply a list of ingredient IDs.")
    if not target_ids:
        return failure("NEEDS_INPUT", "Choose at least one ingredient to replace.")
    if len(target_ids) > MAX_TARGETS or len(set(target_ids)) != len(target_ids):
        return failure("UNSUPPORTED_INPUT", "Choose up to three distinct targets.")
    if set(target_ids) - catalog.ingredients.keys():
        return failure("UNSUPPORTED_INPUT", "A target ID is outside the catalogue.")
    if set(target_ids) - {item["ingredient_id"] for item in recipe["ingredients"]}:
        return failure("NEEDS_INPUT", "Choose targets present in this recipe.")
    return None


def generate_candidate_lists(recipe, target_ids, constraints, catalog, mode="full", diagnostics=None):
    """Use original instruction clauses and only non-targets for retained context."""
    from .substitute import rank

    pools = {}
    for target in target_ids:
        result = rank(catalog, recipe, target, constraints, MAX_CANDIDATES_PER_TARGET, mode,
                      other_targets=set(target_ids) - {target})
        pools[target] = result.items
        if diagnostics is not None:
            diagnostics[target] = {"status": result.status, "warnings": result.warnings,
                                   "reason_counts": result.reason_counts}
    return pools


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
            "rule": blocked_rule,
            "warning": None,
        }

    if matching_rules:
        rule = min(matching_rules, key=lambda row: row["score"])
        return {
            "score": rule["score"],
            "blocked": False,
            "source": "reviewed_pair_rule",
            "rule": rule,
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
            "unknown_evidence": bool(compatibility["warning"]),
            **({"rule": compatibility["rule"]} if "rule" in compatibility else {}),
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


def generate_joint_plans(candidate_lists, catalog, recipe, constraints=None, *, top_k=3, counts=None):
    """Generate and rank valid combinations of replacement candidates."""

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

        scored = score_joint_plan(
            selected,
            catalog,
            recipe,
            target_ids,
        )

        if not scored["valid"]:
            if counts is not None:
                counts[scored["reason"]] += 1
            continue

        plan = {
            "target_ids": target_ids,
            "replacement_ids": list(replacement_ids),
            "replacements": dict(zip(target_ids, replacement_ids)),
            "score": scored["score"],
            "component_scores": scored["component_scores"],
            "pair_details": scored["pair_details"],
            "warnings": list(dict.fromkeys(scored["warnings"])),
            "purchase_count": sum(bool(c.get("purchase_required")) for c in selected),
        }
        if constraints is not None:
            plan["purchase_ids"] = sorted(set(replacement_ids) - set(constraints.pantry_ids))
            plan["purchase_count"] = len(plan["purchase_ids"])
            checks = validate_plan(recipe, target_ids, plan, constraints, catalog)
            if not checks["valid"]:
                if counts is not None:
                    counts.update(checks["errors"])
                continue
            plan["constraint_checks"] = checks
            plan["final_ids"] = checks["final_ingredient_ids"]
            plan["individual_scores"] = [c["score"] for c in selected]
            partial = [target for target, candidate in zip(target_ids, selected) if candidate.get("partial_evidence")]
            if partial:
                plan["warnings"].append("Partial individual evidence for " + ", ".join(partial) + ".")
        plans.append(plan)

    plans.sort(
        key=lambda plan: (
            -plan["score"],
            plan["purchase_count"],
            tuple(plan["replacement_ids"]),
        )
    )

    return plans[:min(top_k, 3)]


def generate_independent_baseline(candidate_lists, target_ids=None, catalog=None, recipe=None, constraints=None):
    """Choose the best eligible candidate for each target and preserve any violations."""
    from math import fsum, isfinite

    targets = list(candidate_lists if target_ids is None else target_ids)

    def failure(message):
        return {"target_ids": targets, "replacement_ids": [], "score": None, "joint_score": None,
                "violations": [message], "valid": False}

    if not targets:
        return failure("No replacement targets supplied.")
    if len(targets) > MAX_TARGETS:
        return failure("At most three replacement targets are allowed.")
    if len(set(targets)) != len(targets):
        return failure("Duplicate requested target IDs.")
    if (catalog is None) != (recipe is None) or (constraints is not None and catalog is None):
        return failure("Both catalog and recipe are required for plan validation.")

    selected = []
    for target in targets:
        group = candidate_lists.get(target, [])[:MAX_CANDIDATES_PER_TARGET]
        if not group:
            return failure(f"No candidates available for target {target}.")
        for candidate in group:
            if not isinstance(candidate, dict):
                return failure(f"Invalid candidate record for target {target}.")
            if not isinstance(candidate.get("candidate_id"), str) or not candidate["candidate_id"]:
                return failure(f"Invalid candidate ID for target {target}.")
            score = candidate.get("score")
            if type(score) not in (int, float) or not isfinite(score) or not 0 <= score <= 1:
                return failure(f"Invalid candidate score for target {target}.")
        selected.append(min(group, key=lambda c: (-c["score"], c["candidate_id"])))

    ids = [c["candidate_id"] for c in selected]
    scores = [c["score"] for c in selected]
    baseline = {"target_ids": targets, "replacement_ids": ids, "replacements": dict(zip(targets, ids)),
                "individual_scores": scores, "score": fsum(scores) / len(scores), "joint_score": None}
    if constraints is not None:
        checks = validate_plan(recipe, targets, baseline, constraints, catalog)
        baseline.update(constraint_checks=checks, valid=checks["valid"], violations=checks["errors"])
        if checks["valid"]:
            baseline["joint_score"] = score_joint_plan(selected, catalog, recipe, targets)["score"]
        return baseline

    # Legacy helper callers can supply synthetic pools without a complete catalogue.
    violations = []
    if len(set(ids)) != len(ids):
        violations.append("Duplicate replacement IDs selected.")
    if set(ids).intersection(targets):
        violations.append("A target ingredient was selected as a replacement.")
    if catalog is not None:
        roles = [target_role_context(recipe, t, catalog)["roles"] for t in targets]
        for i, j in combinations(range(len(ids)), 2):
            if pair_compatibility_score(ids[i], ids[j], catalog, roles[i] | roles[j])["blocked"]:
                violations.append(f"Blocked replacement pair: {ids[i]}, {ids[j]}.")
    return {**baseline, "valid": not violations, "violations": violations}


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
        if target_id not in recipe_ids:
            errors.append(f"Target {target_id} must occur in the recipe.")

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

    if mapping_is_safe and set(recipe_ids + target_ids) <= catalog.ingredients.keys():
        from .roles import target_clauses
        from .substitute import directed_blocks

        if getattr(catalog, "pairs", []):
            for target, candidate in zip(plan_targets, replacement_ids):
                clauses = target_clauses(recipe, target, catalog.ingredients, catalog.policy["shorthand"])
                roles = target_role_context(recipe, target, catalog)
                if candidate in directed_blocks(catalog, target, roles, clauses):
                    errors.append(f"Blocked substitution: {target} to {candidate}.")

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

    if "replacements" in plan and plan["replacements"] != dict(zip(plan_targets, replacement_ids)):
        errors.append("Replacement mapping disagrees with the target and replacement lists.")
    if "final_ids" in plan and plan["final_ids"] != final_ids:
        errors.append("Final IDs disagree with the reconstructed recipe.")
    purchases = sorted(set(replacement_ids) - set(constraints.pantry_ids))
    if "purchase_ids" in plan and plan["purchase_ids"] != purchases:
        errors.append("Purchase IDs disagree with the available pantry.")
    if "purchase_count" in plan and plan["purchase_count"] != len(purchases):
        errors.append("Purchase count disagrees with the available pantry.")
    return {
        "valid": not errors,
        "errors": errors,
        "final_ingredient_ids": final_ids,
    }
