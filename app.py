
"""KitchenCompass Phase 2 Streamlit application."""

import streamlit as st

from kitchencompass.service import recommend_for_pantry


st.set_page_config(
    page_title="KitchenCompass",
    page_icon="🍲",
    layout="wide",
)

st.title("🍲 KitchenCompass")
st.subheader("Recipe discovery based on your available ingredients")

st.write(
    "Enter the ingredients you have, add any exclusions, "
    "and discover recipes that match your pantry."
)

st.divider()

with st.form("recommendation_form"):
    pantry_text = st.text_input(
        "Pantry ingredients",
        placeholder="Example: potato, tomato, onion, water",
        help="Separate ingredient names with commas.",
    )

    excluded_text = st.text_input(
        "Ingredients to exclude (optional)",
        placeholder="Example: milk, peanuts",
        help="Recipes containing excluded ingredients or their "
             "known compound ingredients will be filtered out.",
    )

    submitted = st.form_submit_button(
        "Find recipes",
        type="primary",
    )


if submitted:
    pantry_names = [
        item.strip()
        for item in pantry_text.split(",")
        if item.strip()
    ]

    excluded_names = [
        item.strip()
        for item in excluded_text.split(",")
        if item.strip()
    ]

    try:
        result = recommend_for_pantry(
            pantry_names=pantry_names,
            excluded_names=excluded_names,
        )

        st.divider()
        st.header("Your recipe recommendations")

        if result.status == "NEEDS_INPUT":
            st.warning(
                "Please enter at least one pantry ingredient."
            )

        elif result.status == "UNSUPPORTED_INPUT":
            st.error("An ingredient could not be resolved.")
            for warning in result.warnings:
                st.write(warning)

        elif result.status == "UNRESOLVED_EXCLUSION":
            st.error("An exclusion could not be resolved.")
            for warning in result.warnings:
                st.write(warning)

        elif result.status == "NO_FEASIBLE_RESULT":
            st.warning(
                "No recipes satisfy your selected exclusions."
            )
            for warning in result.warnings:
                st.write(warning)

        elif result.status == "OK":
            st.success(
                f"Found {len(result.items)} matching recipes."
            )

            for warning in result.warnings:
                st.caption(warning)

            for index, recipe in enumerate(result.items, start=1):
                with st.container(border=True):
                    st.subheader(
                        f"{index}. {recipe['title']}"
                    )

                    col1, col2, col3 = st.columns(3)

                    col1.metric(
                        "Recommendation score",
                        f"{recipe['score']:.3f}",
                    )
                    col2.metric(
                        "Ingredient coverage",
                        f"{recipe['coverage']:.1%}",
                    )
                    col3.metric(
                        "Missing ingredients",
                        recipe["missing_count"],
                    )

                    st.write(recipe["explanation"])

                    with st.expander("Ingredients you have"):
                        if recipe["matches"]:
                            for item in recipe["matches"]:
                                st.write(f"✓ {item['name']}")
                        else:
                            st.write("No matching ingredients.")

                    with st.expander("Ingredients missing"):
                        if recipe["missing"]:
                            for item in recipe["missing"]:
                                essential_label = (
                                    " (essential)"
                                    if item["essential"]
                                    else ""
                                )
                                st.write(
                                    f"• {item['name']}{essential_label}"
                                )
                        else:
                            st.write(
                                "You have all the required ingredients!"
                            )

        else:
            st.error(f"Unexpected result status: {result.status}")

    except Exception as error:
        st.error("Something went wrong while finding recipes.")
        st.exception(error)


st.divider()
st.caption(
    "KitchenCompass | Phase 2 development | "
    "Recommendations are based on ingredient overlap."
)



# --------------------------------------------------
# Custom recipe creation and JSON import/export
# --------------------------------------------------

from kitchencompass.custom_recipes import (
    create_custom_recipe,
    export_custom_recipe,
    import_custom_recipe,
)

import json


if "custom_recipes" not in st.session_state:
    st.session_state.custom_recipes = {}


st.divider()
st.header("Create your own recipe")

st.write(
    "Add a personal recipe. It stays in your current session "
    "and is not added to the shared recipe catalogue."
)

with st.form("custom_recipe_form"):
    custom_title = st.text_input(
        "Recipe title",
        placeholder="Example: My Potato Curry",
    )

    custom_ingredients_text = st.text_area(
        "Ingredients (one per line)",
        placeholder="potato | 200 g\ntomato | 2 medium\nonion | 1 medium",
    )

    custom_instructions_text = st.text_area(
        "Instructions (one step per line)",
        placeholder="Wash and chop the vegetables.\nHeat oil in a pan.\nCook until tender.",
    )

    no_instructions = st.checkbox(
        "Instructions not provided"
    )

    create_submitted = st.form_submit_button(
        "Save custom recipe"
    )


if create_submitted:
    try:
        custom_ingredients = []

        for line in custom_ingredients_text.splitlines():
            if not line.strip():
                continue

            if "|" in line:
                phrase, quantity = line.split("|", 1)
                custom_ingredients.append({
                    "original_phrase": phrase.strip(),
                    "quantity_text": quantity.strip() or None,
                })
            else:
                custom_ingredients.append({
                    "original_phrase": line.strip(),
                    "quantity_text": None,
                })

        custom_instructions = [
            line.strip()
            for line in custom_instructions_text.splitlines()
            if line.strip()
        ]

        recipe = create_custom_recipe(
            title=custom_title,
            ingredients=custom_ingredients,
            instructions=custom_instructions,
            instructions_not_provided=no_instructions,
        )

        recipe_id = str(recipe.recipe_id)
        st.session_state.custom_recipes[recipe_id] = recipe

        st.success(
            f"Recipe '{recipe.title}' saved in this session."
        )

    except Exception as error:
        st.error(f"Could not create recipe: {error}")


# Display session recipes and export controls.
st.subheader("Your custom recipes")

if st.session_state.custom_recipes:
    for recipe_id, recipe in st.session_state.custom_recipes.items():
        with st.container(border=True):
            st.write(f"**{recipe.title}**")
            st.caption(f"Recipe ID: {recipe_id}")

            st.write("Ingredients:")
            for ingredient in recipe.ingredients:
                quantity = (
                    f" ({ingredient.quantity_text})"
                    if ingredient.quantity_text else ""
                )
                st.write(
                    f"- {ingredient.original_phrase}{quantity}"
                )

            if recipe.instructions:
                st.write("Instructions:")
                for index, instruction in enumerate(
                    recipe.instructions, start=1
                ):
                    st.write(f"{index}. {instruction}")
            else:
                st.info("Instructions not provided.")

            st.download_button(
                "Export recipe as JSON",
                data=export_custom_recipe(recipe),
                file_name=f"{recipe.title.replace(' ', '_')}.json",
                mime="application/json",
                key=f"export_{recipe_id}",
            )
else:
    st.info("You have not created any custom recipes yet.")


# JSON import.
st.divider()
st.subheader("Import a custom recipe")

uploaded_recipe = st.file_uploader(
    "Choose a KitchenCompass recipe JSON file",
    type=["json"],
    key="custom_recipe_upload",
)

if uploaded_recipe is not None:
    if st.button("Import recipe"):
        try:
            imported = import_custom_recipe(
                uploaded_recipe.getvalue()
            )

            imported_id = str(imported.recipe_id)

            if imported_id in st.session_state.custom_recipes:
                st.error("This recipe ID already exists in your session.")
            else:
                st.session_state.custom_recipes[imported_id] = imported
                st.success(
                    f"Successfully imported '{imported.title}'."
                )

        except Exception as error:
            st.error(f"Import failed: {error}")
