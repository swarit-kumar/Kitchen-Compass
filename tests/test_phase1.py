from collections import Counter
from copy import deepcopy
import json
from math import log
from pathlib import Path
import shutil

import pytest
from pydantic import ValidationError

from kitchencompass.context import build_context
from kitchencompass.data_io import ROOT, read_json, read_records, sha256
from kitchencompass.prepare import prepare
from kitchencompass.schemas import FlavorProfile, Ingredient, Recipe, Result, Source


def test_recipe_contract_rejects_incomplete_or_unknown_version():
    recipe = read_records(ROOT / "data/processed/recipes.jsonl", Recipe)[0].model_dump()
    with pytest.raises(ValidationError):
        Recipe.model_validate({**recipe, "schema_version": "999"})
    with pytest.raises(ValidationError):
        Recipe.model_validate({key: value for key, value in recipe.items() if key != "title"})
    with pytest.raises(ValidationError):
        Result(status="OK", reason_counts={"invalid": -1})


def test_prepare_reproduces_outputs_and_preserves_inputs(tmp_path):
    config = read_json(ROOT / "config/settings.json")
    input_files = [config[key] for key in ("raw_recipes", "curation", "flavor_snapshot")]
    for name in input_files:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    audit = prepare(config, tmp_path)
    assert audit["raw_total_recipes"] == 248
    assert audit["scope_candidate_recipes"] == 224
    assert audit["active_recipes"] >= 200
    assert audit["active_recipes"] == audit["active_distinct_ingredient_sets"]
    assert audit["unresolved_compounds"]["fish sauce"] == 5
    assert audit["unknown_ingredient_names"] == {}
    files = [p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file()]
    for name in files:
        assert sha256(tmp_path / name) == sha256(ROOT / name), name


def test_catalogue_evidence_and_component_references():
    processed = ROOT / "data/processed"
    ingredients = read_records(processed / "ingredients.jsonl", Ingredient)
    sources = {r.source_id for r in read_records(processed / "sources.jsonl", Source)}
    profiles = read_records(processed / "flavors.jsonl", FlavorProfile)
    keys = {r.ingredient_id for r in ingredients}
    assert len(keys) == len(ingredients)
    assert {p.ingredient_id for p in profiles} == keys
    assert len(profiles) == len(keys)
    for ingredient in ingredients:
        assert set(ingredient.components) <= keys
        assert set(ingredient.source_refs) <= sources
    tomato = next(p for p in profiles if p.ingredient_id == "ing_tomato")
    assert tomato.evidence_status == "available"
    assert "pubchem:7795" in tomato.compound_ids
    assert len(tomato.compound_ids) == 271
    assert len(tomato.source_refs) == 1
    assert set(tomato.source_refs) <= sources
    assert len([p for p in profiles if p.evidence_status == "available"]) == 5
    water = next(p for p in profiles if p.ingredient_id == "ing_water")
    assert water.evidence_status == "missing" and water.compound_ids == []


def test_ppmi_uses_only_training_recipes_and_rejects_group_leakage():
    processed = ROOT / "data/processed"
    recipes = read_records(processed / "recipes.jsonl", Recipe)
    ingredients = read_records(processed / "ingredients.jsonl", Ingredient)
    split = read_json(ROOT / "data/benchmark/splits.json")
    context = build_context(recipes, ingredients, split)
    ids = set(split["recipes"]["train"])
    training = [{entry.ingredient_id for entry in recipe.ingredients}
                for recipe in recipes if recipe.recipe_id in ids]
    counts = Counter(key for row in training for key in row)
    assert set(context["training_recipe_ids"]) == ids
    assert context["n_training_recipes"] == len(training)
    assert {key: value for key, value in context["recipe_occurrence_counts"].items() if value} == counts
    first, row = next((key, vector) for key, vector in context["vectors"].items() if vector)
    second = next(iter(row))
    count = sum({first, second} <= ingredients for ingredients in training)
    expected = max(0, log(len(training) * count / (counts[first] * counts[second])))
    assert expected > 0
    assert context["vectors"][first][second] == pytest.approx(expected)
    assert context["vectors"][second][first] == pytest.approx(expected)
    bad = deepcopy(split)
    bad["groups"]["dev"].append(bad["groups"]["train"][0])
    with pytest.raises(ValueError, match="crosses splits"):
        build_context(recipes, ingredients, bad)


def test_dev_cases_reference_only_development_recipes_and_known_ids():
    rows = [json.loads(line) for line in (ROOT / "data/benchmark/dev_cases.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == len({row["case_id"] for row in rows}) == 15
    assert sum(row["independent_review_requested"] for row in rows) == 10
    dev = set(read_json(ROOT / "data/benchmark/splits.json")["recipes"]["dev"])
    recipes = {row.recipe_id: row for row in read_records(ROOT / "data/processed/recipes.jsonl", Recipe)}
    ingredients = {row.ingredient_id for row in read_records(ROOT / "data/processed/ingredients.jsonl", Ingredient)}
    for row in rows:
        assert row["split"] == "dev" and row["recipe_id"] in dev
        recipe = recipes[row["recipe_id"]]
        assert row["duplicate_group_id"] == recipe.duplicate_group_id
        assert set(row["targets"]) <= {entry.ingredient_id for entry in recipe.ingredients}
        assert (set(row["pantry_ids"]) | set(row["exclusions"])) <= ingredients
        assert len({option["candidate_id"] for option in row["candidate_options"]}) >= 3
        for option in row["candidate_options"]:
            if row["task_type"] == "pantry":
                assert option["recipe_id"] in dev
            else:
                replacements = option["replacements"]
                assert set(replacements) == set(row["targets"])
                assert set(replacements.values()) <= set(row["pantry_ids"])
        if row["review_status"] == "pending_review":
            assert not row["candidate_judgments"] and not row["annotator_ids"]


def test_manifest_hashes_match_packaged_files():
    manifest = read_json(ROOT / "artifacts/manifest.json")
    for file_group in ("input_sha256", "output_sha256"):
        for name, expected in manifest[file_group].items():
            assert sha256(ROOT / Path(name)) == expected, name



def test_expanded_snapshot_preserves_starter_and_groups_related_variants():
    original_path = ROOT / "data/raw/KitchenCompass_Recipes_v1.json"
    original = read_json(original_path)
    expanded = read_json(ROOT / "data/raw/KitchenCompass_Recipes_v2.json")
    assert expanded["parent_snapshot"]["sha256"] == sha256(original_path)
    assert expanded["recipes"][:len(original["recipes"])] == original["recipes"]

    recipes = read_records(ROOT / "data/processed/recipes.jsonl", Recipe)
    by_id = {recipe.recipe_id: recipe for recipe in recipes}
    curation = read_json(ROOT / "data/curation/catalogue.json")
    for recipe_group in curation["recipe_groups"]:
        present = [by_id[recipe_id] for recipe_id in recipe_group if recipe_id in by_id]
        assert len({recipe.duplicate_group_id for recipe in present}) <= 1

    source_ids = {s.source_id for s in read_records(ROOT / "data/processed/sources.jsonl", Source)}
    assert {recipe.source_ref for recipe in recipes} <= source_ids
