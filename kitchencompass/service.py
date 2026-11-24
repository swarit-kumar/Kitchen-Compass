"""Public service used by both the Streamlit application and development evaluation."""
from functools import lru_cache
from pathlib import Path

from .catalog import Catalog, load_jsonl
from .constraints import ConstraintEngine
from .custom_recipes import CustomRecipe
from .data_io import ROOT
from .normalize import IngredientNormalizer
from .recommend import recommend_recipes as rank_pantry
from .schemas import Constraints, Recipe, Result
from .substitute import rank


@lru_cache(maxsize=2)
def get_catalog(snapshot_key=None):
    """Only public catalogue inputs are cached. Callers can pass the manifest digest."""
    return Catalog()


def normalize_inputs(raw_names, catalog):
    resolved, suggestions = [], {}
    for name in raw_names:
        match = catalog.normalizer.resolve(name)
        if match["status"] == "RESOLVED":
            resolved.append(match["ingredient_id"])
        else:
            suggestions[name] = match["suggestions"]
    return {"resolved_ids": list(dict.fromkeys(resolved)), "unresolved_names": list(suggestions),
            "suggestions_by_name": suggestions}


def confirm_custom_recipe(recipe, catalog, confirmations=None):
    """Keep every original line. Store confirmed IDs for legacy names and free text."""
    confirmations = confirmations or {}
    entries = []
    for index, entry in enumerate(recipe.ingredients):
        match = catalog.normalizer.resolve(entry.original_phrase)
        selected = confirmations.get(index, entry.ingredient_id)
        exact = match["ingredient_id"]
        if selected is not None and selected not in catalog.ingredients:
            raise ValueError(f"Ingredient {index + 1}: unknown confirmed ingredient ID.")
        if exact and selected and exact != selected:
            raise ValueError(f"Ingredient {index + 1}: confirmed ID conflicts with '{entry.original_phrase}'.")
        if match["status"] == "AMBIGUOUS" and selected and selected not in match["suggestions"]:
            raise ValueError(f"Ingredient {index + 1}: select one of the matching ingredients.")
        key = exact or selected
        if not key:
            raise ValueError(f"Ingredient {index + 1}: confirm the catalogue match for '{entry.original_phrase}'. Suggestions: {match['suggestions']}")
        entries.append(entry.model_copy(update={"ingredient_id": key}))
    if len({entry.ingredient_id for entry in entries}) < 2:
        raise ValueError("Use at least two distinct supported ingredients. Repeated lines count once.")
    return recipe.model_copy(update={"ingredients": entries})


def validate_recipe(recipe, catalog):
    try:
        if isinstance(recipe, str):
            if recipe not in catalog.recipes:
                raise ValueError("Unknown catalogue recipe.")
            row = catalog.recipes[recipe]
        elif isinstance(recipe, CustomRecipe):
            custom = confirm_custom_recipe(recipe, catalog)
            row = {"recipe_id": str(custom.recipe_id), "title": custom.title, "dish_family": "other",
                   "ingredients": [entry.model_dump() for entry in custom.ingredients],
                   "instructions": list(custom.instructions)}
        else:
            row = (recipe if isinstance(recipe, Recipe) else Recipe.model_validate(recipe)).model_dump()
        ids = {item["ingredient_id"] for item in row["ingredients"]}
        if len(ids) < 2 or ids - catalog.ingredients.keys():
            raise ValueError("The recipe needs at least two distinct catalogue ingredients and all entries must resolve.")
        return {"valid": True, "recipe": row, "errors": [], "warnings": []}
    except ValueError as error:
        return {"valid": False, "recipe": None, "errors": [str(error)], "warnings": []}


def _check_constraints(constraints, ingredients, versions):
    for values, status, field in [(constraints.excluded_ids, "UNRESOLVED_EXCLUSION", "exclusion"),
                                  (constraints.pantry_ids, "UNSUPPORTED_INPUT", "pantry")]:
        unknown = sorted(set(values) - ingredients.keys())
        if unknown:
            return Result(status=status, warnings=[f"Unknown {field} ingredient IDs: {', '.join(unknown)}."], **versions)
    return None


def _pantry_result(rows, ingredients, engine, pantry, constraints, top_k, mode, versions):
    invalid = _check_constraints(constraints, ingredients, versions)
    if invalid:
        return invalid
    if not pantry:
        return Result(status="NEEDS_INPUT", warnings=["Enter at least one pantry ingredient."], **versions)
    result = rank_pantry(rows, ingredients.values(), pantry, constraints.excluded_ids,
                         limit=top_k, mode=mode, engine=engine)
    if not result["items"]:
        return Result(status="NO_FEASIBLE_RESULT", reason_counts={"excluded_by_constraints": len(rows)},
                      warnings=["No recipes satisfy these constraints."], **versions)
    warnings = []
    if result["expanded_exclusions"]:
        warnings.append("Excluded ingredients and their known compounds: " + ", ".join(
            ingredients[key]["display_name"] for key in result["expanded_exclusions"]))
    return Result(status="OK", items=result["items"], warnings=warnings, **versions)


def recommend_recipes(pantry_ids, constraints, top_k=5, *, mode="weighted", catalog=None):
    catalog = catalog or get_catalog()
    constraints = Constraints.model_validate(constraints)
    pantry = list(dict.fromkeys(pantry_ids))
    constraints = constraints.model_copy(update={"pantry_ids": pantry})
    return _pantry_result(catalog.recipes.values(), catalog.ingredients, catalog.constraints, pantry,
                         constraints, top_k, mode, catalog.versions)


def recommend_for_pantry(pantry_names, excluded_names=None, data_dir="data/processed", limit=5, *, mode="weighted", catalog=None):
    """Preserve the Phase 2 names-based API, including its optional catalogue directory."""
    catalog = catalog or get_catalog()
    normalizer, ingredients, rows, engine = catalog.normalizer, catalog.ingredients, catalog.recipes.values(), catalog.constraints
    if Path(data_dir) != Path("data/processed") and Path(data_dir).resolve() != ROOT / "data/processed":
        raw = load_jsonl(Path(data_dir) / "ingredients.jsonl")
        normalizer = IngredientNormalizer(raw)
        ingredients, rows, engine = normalizer.ingredients, load_jsonl(Path(data_dir) / "recipes.jsonl"), ConstraintEngine(raw)
        if any(item["ingredient_id"] not in ingredients for row in rows for item in row["ingredients"]):
            return Result(status="UNSUPPORTED_INPUT", warnings=["A recipe references an unknown ingredient."], **catalog.versions)
    ids = []
    for names, status in [(excluded_names or [], "UNRESOLVED_EXCLUSION"), (pantry_names, "UNSUPPORTED_INPUT")]:
        resolved = []
        for name in names:
            match = normalizer.resolve(name)
            if not match["ingredient_id"]:
                suggestions = ", ".join(ingredients[key]["display_name"] for key in match["suggestions"])
                return Result(status=status, warnings=[f"Confirm a supported ingredient for '{name}'."
                              + (f" Suggestions: {suggestions}." if suggestions else "")], **catalog.versions)
            resolved.append(match["ingredient_id"])
        ids.append(resolved)
    excluded, pantry = ids
    constraints = Constraints(pantry_ids=pantry, excluded_ids=excluded)
    return _pantry_result(rows, ingredients, engine, pantry, constraints, limit, mode, catalog.versions)


def rank_substitutes(recipe, target_id, constraints, top_k=5, *, mode="full", catalog=None, complete_only=False, audit=None):
    catalog = catalog or get_catalog()
    constraints = Constraints.model_validate(constraints)
    invalid = _check_constraints(constraints, catalog.ingredients, catalog.versions)
    if invalid:
        return invalid
    validated = validate_recipe(recipe, catalog)
    if not validated["valid"]:
        return Result(status="UNSUPPORTED_INPUT", warnings=validated["errors"], **catalog.versions)
    return rank(catalog, validated["recipe"], target_id, constraints, top_k, mode, complete_only, audit)


def adapt_recipe(recipe, target_ids, constraints, top_k=3, *, catalog=None, audit=None):
    """Rank up to three plans. An optional audit receives the same-pool baseline."""
    from collections import Counter
    from math import prod
    from .adapt import (generate_candidate_lists, generate_independent_baseline,
                        generate_joint_plans, validate_targets)

    catalog = catalog or get_catalog()
    versions = catalog.versions
    if audit is not None:
        audit.clear()
        audit.update(candidate_ids={}, combinations=0, baseline=None)
    if type(top_k) is not int or top_k < 1:
        return Result(status="UNSUPPORTED_INPUT", warnings=["Request a positive integer plan limit."], **versions)
    try:
        constraints = Constraints.model_validate(constraints)
    except ValueError as error:
        return Result(status="UNSUPPORTED_INPUT", warnings=[str(error)], **versions)
    invalid = _check_constraints(constraints, catalog.ingredients, versions)
    if invalid:
        return invalid
    validated = validate_recipe(recipe, catalog)
    if not validated["valid"]:
        return Result(status="UNSUPPORTED_INPUT", warnings=validated["errors"], **versions)
    recipe = validated["recipe"]
    invalid = validate_targets(recipe, target_ids, catalog)
    if invalid:
        return invalid
    if len(target_ids) > constraints.max_replacements:
        return Result(status="UNSUPPORTED_INPUT", warnings=["The selected targets exceed max_replacements."], **versions)
    retained = {item["ingredient_id"] for item in recipe["ingredients"]} - set(target_ids)
    conflicts = sorted(retained.intersection(catalog.constraints.expand_exclusions(constraints.excluded_ids)))
    if conflicts:
        names = ", ".join(catalog.ingredients[key]["display_name"] for key in conflicts)
        return Result(status="UNRESOLVED_EXCLUSION", reason_counts={"retained_exclusions": len(conflicts)},
                      warnings=[f"Retained ingredients conflict with your exclusions: {names}. Include them among the targets or revise the exclusions."],
                      **versions)

    diagnostics = {}
    pools = generate_candidate_lists(recipe, target_ids, constraints, catalog, diagnostics=diagnostics)
    if audit is not None:
        audit.update(candidate_ids={key: [c["candidate_id"] for c in group] for key, group in pools.items()},
                     combinations=prod(map(len, pools.values())), target_diagnostics=diagnostics,
                     baseline=generate_independent_baseline(pools, target_ids, catalog, recipe, constraints))
    empty = [key for key, group in pools.items() if not group]
    if empty:
        reasons = Counter({"targets_without_candidates": len(empty)})
        for key in empty:
            reasons.update(diagnostics[key]["reason_counts"])
        return Result(status="NO_FEASIBLE_RESULT", reason_counts=dict(reasons),
                      warnings=["No eligible replacement for " + ", ".join(catalog.ingredients[k]["display_name"] for k in empty) + "."],
                      **versions)

    counts = Counter()
    plans = generate_joint_plans(pools, catalog, recipe, constraints, top_k=top_k, counts=counts)
    warnings = (["Quantities and instructions are the originals. You may need to adjust the preparation."]
                if plans else ["Every candidate combination failed a whole-plan check."])
    if not recipe["instructions"]:
        warnings.append("No instructions supplied. The planner used catalogue roles.")
    return Result(status="OK" if plans else "NO_FEASIBLE_RESULT", items=plans,
                  reason_counts=dict(counts), warnings=warnings, **versions)
