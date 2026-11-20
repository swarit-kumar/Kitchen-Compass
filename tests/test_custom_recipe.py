import json

import pytest

from kitchencompass.custom_recipes import create_custom_recipe, export_custom_recipe, import_custom_recipe
from kitchencompass.schemas import Constraints
from kitchencompass.service import confirm_custom_recipe, get_catalog, rank_substitutes


def test_legacy_json_and_explicit_confirmation_round_trip():
    legacy = {"schema_version": "1.0", "recipe_id": "34fb737c-48e3-4bcd-9e69-257b96431642",
              "title": "My soup", "ingredients": [{"original_phrase": "finely sliced onion", "quantity_text": "half"},
              {"original_phrase": "aloo"}], "instructions": [], "instructions_not_provided": True}
    draft = import_custom_recipe(json.dumps(legacy))
    assert draft.schema_version == "2.0"
    cat = get_catalog()
    assert rank_substitutes(draft, "ing_onion", Constraints()).status == "UNSUPPORTED_INPUT"
    confirmed = confirm_custom_recipe(draft, cat, {0: "ing_onion"})
    assert confirmed.ingredients[0].original_phrase == "finely sliced onion"
    assert confirmed.ingredients[0].quantity_text == "half"
    assert confirmed.ingredients[1].ingredient_id == "ing_potato"
    assert import_custom_recipe(export_custom_recipe(confirmed)) == confirmed
    result = rank_substitutes(confirmed, "ing_onion", Constraints(pantry_ids=["ing_garlic"], pantry_only=True))
    assert result.items and any("No instructions" in w for w in result.warnings)
    assert result.items[0]["role_evidence"]["rule_ids"] == []


def test_conflicting_unknown_duplicate_and_repeated_mappings():
    cat = get_catalog()
    draft = create_custom_recipe("Soup", [{"original_phrase": "aloo"}, {"original_phrase": "potato"}], ["Boil."])
    with pytest.raises(ValueError, match="distinct"):
        confirm_custom_recipe(draft, cat)
    with pytest.raises(ValueError, match="conflicts"):
        confirm_custom_recipe(draft, cat, {0: "ing_tomato"})
    with pytest.raises(ValueError, match="unknown"):
        confirm_custom_recipe(draft, cat, {0: "not_in_catalogue"})
    triple = create_custom_recipe("Soup", [{"original_phrase": "aloo"}, {"original_phrase": "potato"},
                                        {"original_phrase": "tomato", "essential": True}], ["Boil."])
    confirmed = confirm_custom_recipe(triple, cat)
    assert len(confirmed.ingredients) == 3 and confirmed.ingredients[2].essential


def test_import_size_and_malformed_json():
    for payload in (b"{" , b" " * 1048577):
        with pytest.raises(ValueError):
            import_custom_recipe(payload)
