"""Prepare the Phase 1 catalogue from checked-in raw data and curation."""
from collections import Counter, defaultdict
from itertools import combinations
import random
import re

from .data_io import ROOT, index_by, read_json, sha256, write_json, write_records
from .schemas import FlavorProfile, Ingredient, RawRecipe, Recipe, RecipeIngredient, RoleRule, Source


def normalize(text):
    return " ".join(text.casefold().strip().split())


def ingredient_id(name):
    return "ing_" + re.sub(r"[^a-z0-9]+", "_", normalize(name)).strip("_")


def recipe_signature(recipe):
    return frozenset(i.ingredient_id for i in recipe.ingredients)


def make_groups(recipes, manual_groups):
    by_id = index_by(recipes, "recipe_id")
    parents = {key: key for key in by_id}

    def root(key):
        while parents[key] != key:
            key = parents[key]
        return key

    def merge(first, second):
        a, b = sorted((root(first), root(second)))
        parents[b] = a

    for group in manual_groups:
        present = [key for key in group if key in by_id]
        for first, second in zip(present, present[1:]):
            merge(first, second)

    signatures = {key: recipe_signature(recipe) for key, recipe in by_id.items()}
    for (first, a), (second, b) in combinations(signatures.items(), 2):
        if len(a & b) / len(a | b) >= 0.85:
            merge(first, second)
    return [
        recipe.model_copy(update={"duplicate_group_id": "group_" + root(recipe.recipe_id)[4:]})
        for recipe in recipes
    ]


def make_splits(recipes, seed, fractions, revision="v1"):
    if set(fractions) != {"train", "dev", "test"} or any(x <= 0 for x in fractions.values()) or abs(sum(fractions.values()) - 1) > 1e-9:
        raise ValueError("Split fractions must be positive and sum to 1")
    groups = defaultdict(list)
    for recipe in recipes:
        groups[recipe.duplicate_group_id].append(recipe.recipe_id)
    if len(groups) < 3:
        raise ValueError("At least three active recipe groups are required")
    ordered_groups = sorted(groups)
    random.Random(seed).shuffle(ordered_groups)
    n_dev = max(1, round(len(groups) * fractions["dev"]))
    n_test = max(1, round(len(groups) * fractions["test"]))
    if n_dev + n_test >= len(groups):
        raise ValueError("Split leaves no training groups")
    buckets = {
        "dev": ordered_groups[:n_dev],
        "test": ordered_groups[n_dev:n_dev + n_test],
        "train": ordered_groups[n_dev + n_test:],
    }
    return {
        "split_id": f"groups_seed_{seed}_{revision}",
        "seed": seed,
        "fractions_requested": fractions,
        "groups": {name: sorted(ids) for name, ids in buckets.items()},
        "recipes": {name: sorted(rid for group in ids for rid in groups[group]) for name, ids in buckets.items()},
    }


def validate_components(metadata, definitions):
    def visit(name, ancestors):
        if name not in metadata:
            raise ValueError(f"Unknown component: {name}")
        if name in ancestors:
            raise ValueError(f"Cyclic component: {name}")
        for child in definitions.get(name, []):
            visit(child, ancestors | {name})

    for name in definitions:
        if not definitions[name] or len(set(definitions[name])) != len(definitions[name]):
            raise ValueError(f"Empty or duplicate component list for {name}")
        visit(name, set())


def prepare(config, root=ROOT):
    raw_path = root / config["raw_recipes"]
    curation_path = root / config["curation"]
    snapshot_path = root / config["flavor_snapshot"]
    raw = read_json(raw_path)
    if config["schema_version"] != "1.0" or raw["raw_format_version"] != "1.0":
        raise ValueError("Unsupported schema version")
    if raw["data_version"] != config["data_version"]:
        raise ValueError("Recipe snapshot version differs from configuration")

    curation = read_json(curation_path)
    metadata = curation["ingredient_metadata"]
    definitions = curation["component_definitions"]
    validate_components(metadata, definitions)
    unsupported = set(curation["unresolved_preparations"])
    aliases = {}
    for name in sorted(metadata):
        for alias in [name, *curation["alias_overrides"].get(name, [])]:
            key = normalize(alias)
            if key in aliases and aliases[key] != name:
                raise ValueError(f"Ambiguous ingredient alias: {alias}")
            aliases[key] = name

    recipe_sources = raw["sources"] if "sources" in raw else [raw["source"]]
    recipe_source_ids = {source["source_id"] for source in recipe_sources}
    curation_source_id = f"src_kc_project_curation_{config['split_revision']}" if "split_revision" in config else "src_kc_project_curation_v1"
    sources = [
        Source(source_id=source["source_id"], title=source["title"],
               local_filename=source.get("local_filename", config["raw_recipes"]),
               accessed_date="2026-11-12", locator=source.get("locator", "recipes array"),
               license_status="Project-generated draft; no external recipe text",
               permitted_uses=["KitchenCompass course project"])
        for source in recipe_sources
    ]
    sources.append(Source(source_id=curation_source_id, title="KitchenCompass proposed catalogue curation",
                          local_filename=config["curation"], accessed_date="2026-11-12",
                          locator="roles, component definitions and essential_by_recipe",
                          license_status="Project-authored curation; pending team review",
                          permitted_uses=["KitchenCompass course project"]))
    raw_recipes = sorted(index_by([RawRecipe.model_validate(r) for r in raw["recipes"]], "recipe_id").values(),
                         key=lambda recipe: recipe.recipe_id)
    names_by_recipe = {}
    accepted = []
    excluded = {}
    unknown_names = Counter()
    unresolved_compounds = Counter()
    signatures = {}
    for recipe in raw_recipes:
        if recipe.source_ref not in recipe_source_ids:
            raise ValueError(f"Unknown source in {recipe.recipe_id}")
        if recipe.dish_family not in config["dish_families"]:
            excluded[recipe.recipe_id] = ["outside_dish_family_scope"]
            continue
        reasons = set()
        entries = []
        essentials = curation["essential_by_recipe"].get(recipe.recipe_id)
        if not essentials:
            reasons.add("essential_review_missing")
            essentials = {}
        for item in recipe.ingredients:
            name = aliases.get(normalize(item.ingredient_name_hint))
            if name is None:
                unknown_names[item.ingredient_name_hint] += 1
                reasons.add(f"unmapped_ingredient:{item.ingredient_name_hint}")
                continue
            if name in unsupported or (item.compound_review_required and name not in definitions):
                unresolved_compounds[name] += 1
                reasons.add(f"unresolved_compound:{name}")
            entries.append(RecipeIngredient(
                ingredient_id=ingredient_id(name), original_phrase=item.original_phrase,
                quantity_text=item.quantity_text, essential=name in essentials, essential_reason=essentials.get(name),
            ))
        if len({i.ingredient_id for i in entries}) < 2:
            reasons.add("insufficient_distinct_ingredients")
        if not {ingredient_id(name) for name in essentials}.issubset(i.ingredient_id for i in entries):
            reasons.add("essential_ingredient_not_present")
        if reasons:
            excluded[recipe.recipe_id] = sorted(reasons)
            continue
        signature = (
            normalize(recipe.title),
            tuple(sorted((i.ingredient_id, i.quantity_text or "") for i in entries)),
            tuple(normalize(step) for step in recipe.instructions),
        )
        if signature in signatures:
            excluded[recipe.recipe_id] = [f"exact_duplicate_of:{signatures[signature]}"]
            continue
        signatures[signature] = recipe.recipe_id
        accepted.append(Recipe(
            recipe_id=recipe.recipe_id, title=recipe.title, dish_family=recipe.dish_family,
            ingredients=entries, instructions=recipe.instructions, source_ref=recipe.source_ref,
            duplicate_group_id=recipe.recipe_id, schema_version=config["schema_version"],
        ))
        names_by_recipe[recipe.recipe_id] = {aliases[normalize(i.ingredient_name_hint)] for i in recipe.ingredients}

    recipes = make_groups(accepted, curation["recipe_groups"])
    direct_names = set().union(*names_by_recipe.values())
    pantry_extras = set(curation.get("additional_pantry_ingredients", []))
    if pantry_extras - metadata.keys():
        raise ValueError(f"Unknown extra pantry ingredients: {sorted(pantry_extras - metadata.keys())}")
    active_names = direct_names | pantry_extras

    def include_components(name):
        for child in definitions.get(name, []):
            if child not in active_names:
                active_names.add(child)
                include_components(child)

    for name in sorted(active_names):
        include_components(name)
    if active_names & unsupported:
        raise ValueError(f"Active components are unresolved: {sorted(active_names & unsupported)}")

    ingredients = []
    for name in sorted(active_names):
        entry = metadata[name]
        ingredient_aliases = sorted(curation["alias_overrides"].get(name, []))
        ingredients.append(Ingredient(
            ingredient_id=ingredient_id(name), display_name=name, aliases=ingredient_aliases,
            category=entry["category"], default_roles=entry["roles"],
            components=sorted(ingredient_id(child) for child in definitions.get(name, [])),
            source_refs=[curation_source_id], schema_version=config["schema_version"],
        ))
    known_ingredients = index_by(ingredients, "ingredient_id")
    if any(item.ingredient_id not in known_ingredients for recipe in recipes for item in recipe.ingredients):
        raise ValueError("Recipe refers to an unknown ingredient")

    snapshot = read_json(snapshot_path)
    flavor_rows = {}
    for entry in snapshot["profiles"]:
        key = ingredient_id(entry["ingredient_name"])
        if key in flavor_rows:
            raise ValueError(f"Duplicate flavor mapping for {key}")
        if key not in known_ingredients:
            continue
        source_id = f"src_flavordb_{entry['entity_id']}"
        sources.append(Source(
            source_id=source_id, title=f"{entry['database']}: {entry['entity_name']}", url=entry["url"],
            local_filename=config["flavor_snapshot"], accessed_date=entry["retrieved_date"], locator=entry["locator"],
            license_status=snapshot["license"], permitted_uses=["Noncommercial course use with attribution and share-alike"],
        ))
        cids = entry["pubchem_ids"]
        if not cids or any(type(cid) is not int or cid <= 0 for cid in cids) or len(cids) != len(set(cids)):
            raise ValueError(f"Invalid PubChem IDs in {key}")
        flavor_rows[key] = FlavorProfile(ingredient_id=key, compound_ids=sorted(f"pubchem:{cid}" for cid in cids),
                                         evidence_status="available", source_refs=[source_id])

    flavors = [flavor_rows.get(key) or FlavorProfile(ingredient_id=key, compound_ids=[], evidence_status="missing",
                                                    source_refs=[]) for key in sorted(known_ingredients)]
    role_rules = []
    for rule in curation["role_rules"]:
        selected_ids = sorted({ingredient_id(name) for name in rule["ingredients"]} & set(known_ingredients))
        if selected_ids:
            role_rules.append(RoleRule(
                rule_id=rule["rule_id"], ingredient_ids=selected_ids, categories=[],
                action_keywords=sorted(rule["action_keywords"]), role=rule["role"],
                priority=rule["priority"], source_refs=[curation_source_id],
            ))
    sources_by_id = index_by(sources, "source_id")
    index_by(role_rules, "rule_id")
    if any(ref not in sources_by_id for record in [*ingredients, *flavors, *role_rules] for ref in record.source_refs):
        raise ValueError("Unknown evidence source reference")
    splits = make_splits(recipes, config["random_seed"], config["split_fractions"], config.get("split_revision", "v1"))
    audit = {
        "schema_version": config["schema_version"],
        "data_version": config["data_version"],
        "raw_input_hashes": {config["raw_recipes"]: sha256(raw_path), config["flavor_snapshot"]: sha256(snapshot_path)},
        "raw_total_recipes": len(raw_recipes),
        "scope_candidate_recipes": sum(r.dish_family in config["dish_families"] for r in raw_recipes),
        "active_recipes": len(recipes),
        "active_distinct_ingredient_sets": len({recipe_signature(r) for r in recipes}),
        "active_by_recipe_source": dict(Counter(r.source_ref for r in recipes)),
        "largest_duplicate_group": max(Counter(r.duplicate_group_id for r in recipes).values()),
        "active_by_family": dict(Counter(r.dish_family for r in recipes)),
        "active_by_group": dict(Counter("Indian" if r.cuisine_label == "India" else "International"
                                      for r in raw_recipes if r.recipe_id in names_by_recipe)),
        "active_ingredients": len(ingredients),
        "direct_recipe_ingredients": len(direct_names),
        "additional_pantry_ingredients": sorted(pantry_extras - direct_names),
        "flavor_profiles_available": len(flavor_rows),
        "ingredient_ids_without_a_modeled_role": [i.ingredient_id for i in ingredients if not i.default_roles],
        "missing_flavor_ingredient_ids": [row.ingredient_id for row in flavors if row.evidence_status == "missing"],
        "excluded_recipes": excluded,
        "unknown_ingredient_names": dict(unknown_names),
        "unresolved_compounds": dict(unresolved_compounds),
        "split_recipe_counts": {name: len(ids) for name, ids in splits["recipes"].items()},
        "split_group_counts": {name: len(ids) for name, ids in splits["groups"].items()},
        "proposed_team_review": curation["review_status"],
        "sources": [s.source_id for s in sources],
    }

    processed = root / "data/processed"
    write_records(processed / "ingredients.jsonl", ingredients)
    write_records(processed / "recipes.jsonl", recipes)
    write_records(processed / "sources.jsonl", sources)
    write_records(processed / "flavors.jsonl", flavors)
    write_json(processed / "role_rules.json", [rule.model_dump() for rule in role_rules])
    write_json(root / "data/benchmark/splits.json", splits)
    write_json(root / "results/data_audit.json", audit)
    return audit
