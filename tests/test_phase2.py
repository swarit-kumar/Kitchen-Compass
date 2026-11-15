
"""Automated tests for KitchenCompass Phase 2."""

import pytest

from kitchencompass.normalize import IngredientNormalizer
from kitchencompass.constraints import ConstraintEngine
from kitchencompass.service import recommend_for_pantry
from kitchencompass.custom_recipes import (
    create_custom_recipe,
    export_custom_recipe,
    import_custom_recipe,
)


def test_ingredient_alias_resolution():
    normalizer = IngredientNormalizer.from_file()

    result = normalizer.resolve("maida")

    assert result["status"] == "RESOLVED"
    assert result["ingredient_id"] == "ing_all_purpose_flour"


def test_nested_milk_exclusion_includes_butter_and_ghee():
    normalizer = IngredientNormalizer.from_file()

    engine = ConstraintEngine(list(normalizer.ingredients.values()))

    milk_id = normalizer.resolve("milk")["ingredient_id"]
    expanded = set(engine.expand_exclusions([milk_id]))

    assert {
        "ing_milk",
        "ing_butter",
        "ing_ghee",
    } <= expanded


def test_empty_pantry_returns_needs_input():
    result = recommend_for_pantry([])

    assert result.status == "NEEDS_INPUT"
    assert result.items == []


def test_unknown_pantry_ingredient_returns_unsupported_input():
    result = recommend_for_pantry(["unknown ingredient"])

    assert result.status == "UNSUPPORTED_INPUT"


def test_unknown_exclusion_returns_unresolved_exclusion():
    result = recommend_for_pantry(
        ["potato"],
        ["unknown exclusion"],
    )

    assert result.status == "UNRESOLVED_EXCLUSION"


def test_recommendation_ranking_is_stable_and_correctly_sorted():
    first = recommend_for_pantry(
        ["potato", "tomato", "water"],
        ["milk"],
    )
    second = recommend_for_pantry(
        ["potato", "tomato", "water"],
        ["milk"],
    )

    assert first.status == "OK"
    assert first.items == second.items
    assert len(first.items) <= 5

    sort_keys = [
        (
            -item["score"],
            item["missing_count"],
            item["recipe_id"],
        )
        for item in first.items
    ]

    assert sort_keys == sorted(sort_keys)

    for item in first.items:
        expected_score = (
            0.8 * item["weighted_coverage"]
            + 0.2 / (1 + item["missing_count"])
        )

        assert item["score"] == pytest.approx(
            expected_score,
            abs=0.000001,
        )


def test_custom_recipe_json_round_trip_preserves_data():
    recipe = create_custom_recipe(
        "My Potato Curry",
        [
            {
                "original_phrase": "potato",
                "quantity_text": "200 g",
            },
            {
                "original_phrase": "tomato",
                "quantity_text": "2 medium",
            },
        ],
        [
            "Wash the vegetables.",
            "Cook until tender.",
        ],
    )

    exported = export_custom_recipe(recipe)
    restored = import_custom_recipe(exported)

    assert restored == recipe
    assert restored.recipe_id == recipe.recipe_id
    assert restored.ingredients[0].quantity_text == "200 g"
    assert restored.instructions == [
        "Wash the vegetables.",
        "Cook until tender.",
    ]


def test_custom_recipe_rejects_unknown_schema_version():
    invalid_json = """
    {
        "recipe_id": "2a8179e6-ca46-438d-8cee-be5f514966ea",
        "title": "Invalid Recipe",
        "ingredients": [
            {"original_phrase": "potato"},
            {"original_phrase": "tomato"}
        ],
        "instructions": ["Cook the ingredients."],
        "instructions_not_provided": false,
        "schema_version": "999"
    }
    """

    with pytest.raises(ValueError):
        import_custom_recipe(invalid_json)


def test_custom_recipe_requires_instructions_or_explicit_notice():
    with pytest.raises(ValueError):
        create_custom_recipe(
            "Recipe Without Instructions",
            [
                {"original_phrase": "potato"},
                {"original_phrase": "tomato"},
            ],
        )

    recipe = create_custom_recipe(
        "Recipe Without Instructions",
        [
            {"original_phrase": "potato"},
            {"original_phrase": "tomato"},
        ],
        instructions_not_provided=True,
    )

    assert recipe.instructions == []
    assert recipe.instructions_not_provided is True
