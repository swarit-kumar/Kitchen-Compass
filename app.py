"""KitchenCompass local Streamlit application."""
import streamlit as st

from kitchencompass.custom_recipes import create_custom_recipe, export_custom_recipe, import_custom_recipe
from kitchencompass.data_io import ROOT, read_json, sha256
from kitchencompass.schemas import Constraints
from kitchencompass.service import adapt_recipe, confirm_custom_recipe, get_catalog, normalize_inputs, rank_substitutes, recommend_for_pantry



st.set_page_config(
    page_title="KitchenCompass | Smart Cooking Assistant",
    page_icon="🍲",
    layout="wide",
    initial_sidebar_state="expanded",
)

# KitchenCompass visual theme

# ===== KITCHENCOMPASS VISUAL THEME =====

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Playfair+Display:wght@600;700;800&display=swap');

:root {
    --cream: #F7F3E9;
    --green: #204B37;
    --dark-green: #173B2B;
    --sage: #DCE7C5;
    --orange: #E99A50;
    --ink: #26352D;
    --muted: #657468;
    --white: #FFFFFF;
}

.stApp {
    background: var(--cream);
    color: var(--ink);
    font-family: 'DM Sans', sans-serif;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Main content */
.block-container {
    max-width: 1350px;
    padding: 2rem 3rem 4rem 3rem;
}

/* Headings */
h1, h2, h3 {
    color: var(--green) !important;
    font-family: 'Playfair Display', Georgia, serif !important;
    font-weight: 700 !important;
}

h1 { font-size: 2.8rem !important; }
h2 { font-size: 2rem !important; }
h3 { font-size: 1.35rem !important; }

p, li, label, .stMarkdown {
    color: var(--ink);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #173B2B, #244D38) !important;
    border-right: none;
}

[data-testid="stSidebar"] > div:first-child {
    padding: 1.5rem 1rem;
}

[data-testid="stSidebar"] * {
    color: #F8F5E9 !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label {
    padding: 10px 12px;
    border-radius: 10px;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: #365D43;
}

/* Widget labels */
[data-testid="stWidgetLabel"] p {
    color: #244B37 !important;
    font-weight: 700 !important;
}

/* Text inputs */
.stTextInput input,
.stTextArea textarea {
    background: #FFFFFF !important;
    color: #26352D !important;
    border: 1px solid #C9D3C6 !important;
    border-radius: 12px !important;
    min-height: 45px;
}

.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
    color: #858D83 !important;
    opacity: 1 !important;
}

.stTextInput input:focus,
.stTextArea textarea:focus {
    border: 2px solid #37694D !important;
    box-shadow: 0 0 0 2px rgba(55, 105, 77, 0.12) !important;
}

/* Select boxes and multiselects */
[data-baseweb="select"] > div {
    background: #FFFFFF !important;
    color: #26352D !important;
    border-color: #C9D3C6 !important;
    border-radius: 10px !important;
}

/* Buttons */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    background: #204B37 !important;
    color: #FFFFFF !important;
    border: 1px solid #204B37 !important;
    border-radius: 11px !important;
    padding: 0.55rem 1.1rem !important;
    font-weight: 700 !important;
    transition: 0.2s ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {
    background: #37694D !important;
    border-color: #37694D !important;
    color: #FFFFFF !important;
    transform: translateY(-1px);
}

/* Primary button */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
    background: #204B37 !important;
    color: #FFFFFF !important;
}

/* Force readable text inside every green button */
.stButton > button *,
.stDownloadButton > button *,
.stFormSubmitButton > button * {
    color: #FFFFFF !important;
}

/* Cards */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF !important;
    border: 1px solid #E5E3D8 !important;
    border-radius: 17px !important;
    padding: 1rem !important;
    box-shadow: 0 4px 15px rgba(35, 60, 43, 0.06);
}

/* Captions */
[data-testid="stCaptionContainer"] {
    color: #596B5E !important;
}

/* Radio and checkbox labels */
[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label {
    color: #26352D !important;
}

/* Expanders */
[data-testid="stExpander"] {
    background: #FFFFFF;
    border: 1px solid #E1E5DA;
    border-radius: 12px;
}

/* Recipe ingredient and instruction text */
[data-testid="stText"],
[data-testid="stText"] *,
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] li {
    color: #26352D !important;
}

/* Hero banner */
.kc-hero {
    background: linear-gradient(110deg, #F4E8D2 0%, #F9F1E4 55%, #E8D8B9 100%);
    border: 1px solid #E5D8C1;
    border-radius: 22px;
    padding: 35px 38px;
    margin-bottom: 25px;
    box-shadow: 0 7px 22px rgba(40, 55, 37, 0.08);
}

.kc-eyebrow {
    color: #B76D37;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 2px;
    margin-bottom: 12px;
}

.kc-hero-title {
    color: #204B37;
    font-family: 'Playfair Display', Georgia, serif;
    font-size: clamp(34px, 4vw, 54px);
    font-weight: 800;
    line-height: 1.15;
}

.kc-hero-subtitle {
    color: #4E6253;
    font-size: 16px;
    margin-top: 12px;
}

.kc-hero-art {
    font-size: 105px;
    text-align: center;
    padding: 10px;
}

/* Sidebar branding */
.kc-sidebar-brand {
    color: #FFFFFF;
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 25px;
    font-weight: 700;
    text-align: center;
}

.kc-sidebar-tagline {
    color: #D8E4D0;
    font-size: 12px;
    text-align: center;
    margin-top: 4px;
}

.kc-sidebar-divider {
    border-top: 1px solid rgba(255,255,255,0.2);
    margin: 20px 0;
}

/* Mobile */
@media (max-width: 768px) {
    .block-container {
        padding: 1.2rem 1rem 3rem;
    }

    .kc-hero {
        padding: 22px;
    }

    .kc-hero-art {
        font-size: 55px;
    }

    h1 { font-size: 2.1rem !important; }
    h2 { font-size: 1.7rem !important; }
}
</style>
""", unsafe_allow_html=True)


# Cache identity explicitly includes the frozen data/config versions and the
# manifest digest, so a new release cannot reuse an older catalogue snapshot.
release_settings = read_json(ROOT / "config/settings.json")
release_cache_key = (
    release_settings["data_version"],
    release_settings["config_version"],
    sha256(ROOT / "artifacts/manifest.json"),
)
try:
    catalog = get_catalog(release_cache_key)
except Exception as error:
    st.error("KitchenCompass could not load its read-only catalogue. Please retry or contact the project team.")
    st.exception(error)
    st.stop()

state = st.session_state
state.setdefault("custom_recipes", {})
names = {key: item["display_name"] for key, item in catalog.ingredients.items()}
ingredient_options = sorted(names, key=names.get)
LABELS = {"full": "Context + role + flavor", "flavor_only": "Flavor only",
          "without_context": "Without recipe context", "without_roles": "Without cooking roles"}
REASONS = {"original_or_retained": "Target or already in the recipe", "outside_pantry": "Outside this pantry",
           "excluded_ingredient": "Excluded directly or through a component", "blocked_pair": "Blocked by a preparation rule",
           "incompatible_or_missing_role": "Incompatible or unknown role", "below_threshold": "Below minimum score",
           "missing_evidence": "Insufficient evidence", "targets_without_candidates": "Targets without eligible replacements", "retained_exclusions": "Retained ingredients in conflict"}

RESULTS_PER_BATCH = 5


def run_service(label, operation):
    """Run a service request with visible loading and error feedback."""
    try:
        with st.spinner(label):
            return operation()
    except Exception as error:
        st.error("The request could not be completed. Please check the inputs and try again.")
        st.exception(error)
        return None


def notices(result):
    if result.status != "OK":
        st.info(f"Request status: {result.status}")
    for message in result.warnings:
        if result.status == "OK":
            st.caption(message)
        else:
            st.warning(message)
    if result.reason_counts:
        with st.expander("Why candidates were filtered"):
            for reason, count in result.reason_counts.items():
                st.write(f"{REASONS.get(reason, reason)} · {count}")


def show_more(count_key, total):
    if total == 0:
        return
    shown = min(state[count_key], total)
    st.caption(f"Showing {shown} of {total}")
    if shown < total:
        next_count = min(RESULTS_PER_BATCH, total - shown)
        st.button(f"Show {next_count} more", key=f"{count_key}_more",
                  on_click=state.update, kwargs={count_key: shown + next_count})


def recipe_details(entries, steps, *, separate_quantities=False):
    st.markdown("**Ingredients**")
    for entry in entries:
        line = entry["original_phrase"]
        if separate_quantities and entry["quantity_text"]:
            line += " · " + entry["quantity_text"]
        st.text(line)
    st.markdown("**Cooking instructions**")
    if steps:
        for number, step in enumerate(steps, 1):
            st.write(f"{number}. {step}")
    else:
        st.caption("Instructions were omitted. Catalogue roles will be used.")



def pantry_page():

    st.markdown("## 🔎 Find a recipe")
    st.write(
        "Enter the ingredients you have. Discover recipes that make "
        "the most of what's already in your kitchen."
    )

    with st.container(border=True):
        st.markdown("### 🧺 Your pantry")
        st.caption("Tell KitchenCompass what you have available.")

        pantry_col, exclude_col = st.columns([1.4, 1])

        with pantry_col:
            pantry = st.text_input(
                "Pantry ingredients",
                value="potato, tomato, onion, water",
                help="Separate ingredient names or aliases with commas."
            )

        with exclude_col:
            excluded = st.text_input(
                "Ingredients to exclude",
                placeholder="e.g. milk, peanuts"
            )

        st.divider()
        st.markdown("### ⭐ Recipe ranking")

        mode = st.radio(
            "Choose how recipes should be ranked",
            ["weighted", "overlap"],
            horizontal=True,
            format_func=lambda k: {
                "weighted": "Weighted match",
                "overlap": "Simple overlap"
            }[k]
        )

        st.caption(
            "Weighted match favors essential ingredients and fewer "
            "missing items. Simple overlap counts each distinct "
            "ingredient once."
        )

        search_button = st.button(
            "Find recipes",
            type="primary",
            use_container_width=True
        )


    query = (pantry, excluded, mode)

    if search_button:
        pantry_names = [
            v.strip() for v in pantry.split(",") if v.strip()
        ]
        excluded_names = [
            v.strip() for v in excluded.split(",") if v.strip()
        ]

        response = run_service(
            "Searching your recipe collection...",
            lambda: (
                recommend_for_pantry(
                    pantry_names,
                    excluded_names,
                    limit=None,
                    mode=mode,
                    catalog=catalog
                ),
                normalize_inputs(
                    pantry_names, catalog
                )["resolved_ids"],
                normalize_inputs(
                    excluded_names, catalog
                )["resolved_ids"],
            ),
        )

        if response is None:
            return

        result, pantry_ids, excluded_ids = response

        state["pantry_search"] = (
            query, result, pantry_ids, excluded_ids
        )
        state["pantry_count"] = RESULTS_PER_BATCH
        state.pop("viewed_recipe", None)

    search = state.get("pantry_search")

    if search is None or search[0] != query:
        state.pop("pantry_search", None)
        return

    _, result, pantry_ids, excluded_ids = search

    st.markdown("## 🍽️ Recipe recommendations")
    notices(result)

    if not result.items:
        st.info(
            "No recipes match these pantry ingredients and exclusions. "
            "Try changing your inputs."
        )


    for index, row in enumerate(
        result.items[:state["pantry_count"]], 1
    ):
        with st.container(border=True):
            st.subheader(f"{index}. {row['title']}")

            metric1, metric2, metric3 = st.columns(3)

            metric1.metric(
                "Match score", f"{row['score']:.3f}"
            )
            metric2.metric(
                "Pantry coverage", f"{row['coverage']:.0%}"
            )
            metric3.metric(
                "Missing items", row["missing_count"]
            )

            st.divider()

            available_col, missing_col = st.columns(2)

            with available_col:
                st.markdown("**✅ Ingredients you have**")
                st.write(
                    ", ".join(item["name"] for item in row["matches"])
                    or "None"
                )

            with missing_col:
                st.markdown("**🛒 Ingredients you still need**")
                st.write(
                    ", ".join(
                        item["name"] +
                        (" (essential)" if item["essential"] else "")
                        for item in row["missing"]
                    ) or "Nothing — you have everything!"
                )

            recipe_id = row["recipe_id"]
            expanded = state.get("viewed_recipe") == recipe_id

            view, substitute = st.columns(2)

            view.button(
                "Hide recipe" if expanded else "📖 View recipe",
                key="view_" + recipe_id,
                on_click=state.update,
                kwargs={
                    "viewed_recipe":
                    None if expanded else recipe_id
                },
                use_container_width=True
            )

            substitute.button(
                "Open for substitution",
                key="open_" + recipe_id,
                on_click=open_recipe,
                args=(recipe_id, pantry_ids, excluded_ids),
                use_container_width=True
            )

            if expanded:
                recipe = catalog.recipes[recipe_id]
                recipe_details(
                    recipe["ingredients"],
                    recipe["instructions"]
                )


    show_more("pantry_count", len(result.items))


def open_recipe(recipe_id, pantry=None, excluded=None):
    state["workspace"] = "Substitutions"
    state["sub_recipe"] = recipe_id
    state.pop("sub_target", None)
    state.pop("sub_search", None)
    if pantry is not None:
        state.update(sub_pantry=pantry, sub_excluded=excluded, sub_pantry_only=False, sub_mode="full")


PRESETS = {
    "Paneer masala": ("rec_capsicum_and_paneer_masala", "ing_paneer", ["ing_firm_tofu", "ing_silken_tofu", "ing_cheddar"], ["ing_milk"]),
    "Flavor comparison": ("rec_lemon_coriander_soup", "ing_garlic", ["ing_onion", "ing_potato", "ing_tomato"], []),
    "Instruction match": ("rec_broccoli_cheddar_soup", "ing_all_purpose_flour", ["ing_cornstarch"], []),
    "Impossible pantry": ("rec_capsicum_and_paneer_masala", "ing_paneer", ["ing_cheddar"], ["ing_milk"]),
}


def load_example(label):
    recipe, target, pantry, excluded = PRESETS[label]
    state.pop("sub_search", None)
    state.update(sub_recipe=recipe, sub_target=target, sub_pantry=pantry, sub_excluded=excluded,
                 sub_pantry_only=True, sub_mode="full")



def substitute_page():
    st.header("Ingredient substitution")
    st.write(
        "Find suitable alternatives for an ingredient while "
        "respecting your recipe, pantry and exclusions."
    )

    with st.container(border=True):
        st.markdown("### ✨ Quick examples")
        st.caption("Load an example to explore substitution options.")

        columns = st.columns(2)
        for index, label in enumerate(PRESETS):
            columns[index % 2].button(
                label,
                on_click=load_example,
                args=(label,),
                use_container_width=True
            )

        st.divider()
        st.markdown("### 🍲 Choose your recipe")

        recipes = {
            key: row["title"] for key, row in catalog.recipes.items()
        }
        custom = state["custom_recipes"]
        recipes.update({
            key: f"{row.title} (your recipe)"
            for key, row in custom.items()
        })

        recipe_id = st.selectbox(
            "Recipe",
            sorted(recipes, key=recipes.get),
            format_func=recipes.get,
            key="sub_recipe"
        )

        if recipe_id in custom:
            recipe = custom[recipe_id]
            entries = [e.model_dump() for e in recipe.ingredients]
            steps = recipe.instructions
        else:
            recipe = recipe_id
            entries = catalog.recipes[recipe_id]["ingredients"]
            steps = catalog.recipes[recipe_id]["instructions"]

        with st.expander("View recipe ingredients and instructions"):
            recipe_details(
                entries,
                steps,
                separate_quantities=recipe_id in custom
            )

        options = list(dict.fromkeys(
            entry["ingredient_id"] for entry in entries
        ))
        if state.get("sub_target") not in options:
            state["sub_target"] = options[0]

        st.markdown("### 🔄 Configure your substitution")

        target = st.selectbox(
            "Ingredient to replace",
            options,
            format_func=names.get,
            key="sub_target"
        )

        pantry_col, excluded_col = st.columns(2)

        with pantry_col:
            pantry = st.multiselect(
                "Available replacements in your pantry",
                ingredient_options,
                format_func=names.get,
                key="sub_pantry"
            )

        with excluded_col:
            excluded = st.multiselect(
                "Ingredients to exclude",
                ingredient_options,
                format_func=names.get,
                key="sub_excluded"
            )

        only_col, method_col = st.columns(2)

        with only_col:
            only = st.checkbox(
                "Only suggest ingredients in my pantry",
                key="sub_pantry_only"
            )

        with method_col:
            method = st.selectbox(
                "Substitution method",
                list(LABELS),
                format_func=LABELS.get,
                key="sub_mode"
            )

        query = (
            recipe_id, target, tuple(pantry), tuple(excluded),
            only, method
        )

        st.divider()
        search_button = st.button(
            "Find substitutes",
            type="primary",
            use_container_width=True
        )

    if search_button:
        result = run_service(
            "Finding eligible ingredient replacements...",
            lambda: rank_substitutes(
                recipe, target,
                Constraints(
                    pantry_ids=pantry,
                    excluded_ids=excluded,
                    pantry_only=only
                ),
                top_k=None,
                mode=method,
                catalog=catalog,
            ),
        )
        if result is None:
            return
        state["sub_search"] = (query, result)
        state["sub_count"] = RESULTS_PER_BATCH

    search = state.get("sub_search")
    if search is None or search[0] != query:
        state.pop("sub_search", None)
        return

    _, result = search

    st.subheader(f"Suggested replacements for {names[target]}")
    notices(result)

    if not result.items:
        st.info("No substitutions to show. Try changing your pantry or exclusions.")

    for number, item in enumerate(
        result.items[:state["sub_count"]], 1
    ):
        with st.container(border=True):
            st.subheader(f"{number}. {item['name']}")

            status_col, score_col = st.columns(2)

            with status_col:
                st.caption("AVAILABILITY")
                st.write(
                    "🛒 Purchase required"
                    if item["purchase_required"]
                    else "✅ In your pantry"
                )

            with score_col:
                st.caption("MATCH SCORE")
                st.metric("Score", f"{item['score']:.3f}")

            st.divider()
            st.markdown("**Why this replacement was suggested**")

            for detail in item["reasons"]:
                st.write(detail)

            for clause in item["role_evidence"]["clauses"]:
                st.caption(f"Matched instruction: {clause}")

            if item["partial_evidence"]:
                st.caption(
                    "The score uses the available signals with rescaled weights."
                )

            if item["flavor_sources"]:
                st.caption(
                    "Molecular sources: "
                    + ", ".join(item["flavor_sources"])
                )

    show_more("sub_count", len(result.items))


JOINT_EXAMPLES = {
    "Paneer and pepper": ("rec_black_pepper_paneer", ["ing_paneer", "ing_red_bell_pepper"],
                         ["ing_broccoli", "ing_cheddar", "ing_firm_tofu", "ing_green_bell_pepper", "ing_silken_tofu"]),
    "Chowder comparison": ("rec_new_england_style_fish_chowder", ["ing_butter", "ing_milk"],
                          ["ing_coconut_milk", "ing_olive_oil", "ing_plain_yogurt", "ing_vegetable_oil"]),
}


def load_joint_example(label):
    key, targets, pantry = JOINT_EXAMPLES[label]
    state.update(joint_recipe=key, joint_targets=targets, joint_pantry=pantry,
                 joint_excluded=["ing_milk"], joint_only=True)
    state.pop("joint_search", None)


def joint_page():
    st.header("Joint replacements")
    st.write(
        "Explore coordinated alternatives for multiple ingredients "
        "while preserving recipe constraints."
    )

    with st.container(border=True):
        st.markdown("### ✨ Try an example")
        columns = st.columns(2)
        for col, label in zip(columns, JOINT_EXAMPLES):
            col.button(
                label,
                on_click=load_joint_example,
                args=(label,),
                use_container_width=True
            )

    custom = state["custom_recipes"]
    titles = {key: row["title"] for key, row in catalog.recipes.items()}
    titles.update({key: f"{row.title} (your recipe)" for key, row in custom.items()})
    key = st.selectbox("Recipe", sorted(titles, key=titles.get), format_func=titles.get, key="joint_recipe",
                       on_change=state.pop, args=("joint_targets", None))
    recipe = custom.get(key, key)
    entries = ([e.model_dump() for e in recipe.ingredients] if key in custom else catalog.recipes[key]["ingredients"])
    steps = recipe.instructions if key in custom else catalog.recipes[key]["instructions"]
    with st.expander("Original ingredients and cooking instructions"):
        recipe_details(entries, steps, separate_quantities=key in custom)
    options = list(dict.fromkeys(e["ingredient_id"] for e in entries))
    targets = st.multiselect("Ingredients to replace", options, format_func=names.get,
                             key="joint_targets", max_selections=3)
    pantry = st.multiselect("Available replacements in your pantry", ingredient_options,
                            format_func=names.get, key="joint_pantry")
    excluded = st.multiselect("Ingredients to exclude", ingredient_options, format_func=names.get, key="joint_excluded")
    only = st.checkbox("Only use replacements in my pantry", key="joint_only")
    query = (key, tuple(targets), tuple(pantry), tuple(excluded), only)
    if st.button("Find replacement plans", type="primary"):
        audit = {}
        response = run_service(
            "Evaluating joint replacement plans...",
            lambda: adapt_recipe(
                recipe, targets,
                Constraints(pantry_ids=pantry, excluded_ids=excluded, pantry_only=only),
                catalog=catalog, audit=audit,
            ),
        )
        if response is None:
            return
        state["joint_search"] = (query, response, audit.get("baseline"))
    saved = state.get("joint_search")
    if saved is None or saved[0] != query:
        state.pop("joint_search", None)
        return
    _, result, baseline = saved
    st.divider()
    st.subheader("🍲 Suggested replacement plans")
    notices(result)
    if not result.items:
        st.info("No valid joint replacement plan was found. Try changing the targets, pantry or exclusions.")
    for number, plan in enumerate(result.items, 1):
        with st.container(border=True):
            st.subheader(f"Plan {number}")
            st.markdown("**Ingredient replacements**")
            for target, candidate in plan["replacements"].items():
                left, right = st.columns(2)
                left.info(names[target])
                right.success(names[candidate])
            q, j = plan["component_scores"]["Q"], plan["component_scores"]["J"]
            st.write(f"Plan score {plan['score']:.3f} · Individual quality {q:.3f}"
                     + (f" · Pair compatibility {j:.3f}" if j is not None else ""))
            st.write("Replacement ingredients to buy: " + (", ".join(names[k] for k in plan["purchase_ids"]) or "none"))
            with st.expander("Plan checks and scoring evidence"):
                st.write("Passed final target, pantry, exclusion, duplicate and pair checks.")
                for pair in plan["pair_details"]:
                    basis = "reviewed rule" if pair["source"] == "reviewed_pair_rule" else "training-context similarity"
                    st.write(f"{names[pair['ingredient_a']]} + {names[pair['ingredient_b']]} · {basis} · {pair['score']:.3f}")
                if j is not None:
                    st.caption("Training-context similarity estimates how ingredients fit together. Culinary quality still needs review.")
                for warning in plan["warnings"]:
                    st.caption(warning)
    if baseline and baseline["replacement_ids"]:
        with st.expander("Compare with independent choices"):
            for target, candidate in zip(baseline["target_ids"], baseline["replacement_ids"]):
                st.write(f"{names[target]} → {names[candidate]}")
            if baseline["valid"]:
                st.write(f"Passed plan checks · Joint score {baseline['joint_score']:.3f}")
            else:
                st.warning("Independent choices failed plan checks. " + " ".join(baseline["constraint_checks"]["errors"]))


def custom_page():
    st.header("Your custom recipes")
    st.write(
        "Create your own recipes, confirm their ingredients and "
        "save them for use in KitchenCompass."
    )

    with st.container(border=True):
        st.markdown("### 📝 Create a recipe")

        with st.form("custom_input"):
            title = st.text_input("Recipe title")

            ingredient_col, instruction_col = st.columns(2)

            with ingredient_col:
                lines = st.text_area(
                    "Ingredients (one per line)",
                    placeholder="potato | 200 g\ntomato | 2 medium",
                    help="Use a vertical bar before an optional quantity."
                )

            with instruction_col:
                steps = st.text_area(
                    "Instructions (one step per line)"
                )

            omitted = st.checkbox("Instructions not provided")
            create = st.form_submit_button(
                "Review ingredients",
                type="primary"
            )
    if create:
        state.pop("draft_recipe", None)
        try:
            entries = []
            for line in lines.splitlines():
                if line.strip():
                    phrase, _, quantity = line.partition("|")
                    entries.append({"original_phrase": phrase.strip(), "quantity_text": quantity.strip() or None})
            state["draft_recipe"] = create_custom_recipe(title, entries, [s.strip() for s in steps.splitlines() if s.strip()], omitted)
        except ValueError as error:
            st.error(str(error))

    upload = st.file_uploader("Import a KitchenCompass JSON recipe", type="json")
    if st.button("Review imported recipe", disabled=upload is None):
        state.pop("draft_recipe", None)
        try:
            imported = import_custom_recipe(upload.getvalue())
            if str(imported.recipe_id) in state["custom_recipes"]:
                raise ValueError("This recipe ID already exists in this session.")
            state["draft_recipe"] = imported
        except (ValueError, UnicodeError) as error:
            st.error(f"Could not import this recipe: {error}")

    draft = state.get("draft_recipe")
    if draft:
        st.subheader(f"Confirm ingredients for {draft.title}")
        confirmations = {}
        entries = []
        for i, entry in enumerate(draft.ingredients):
            widget_id = f"{draft.recipe_id}_{i}"
            match = catalog.normalizer.resolve(entry.original_phrase)
            if match["ingredient_id"]:
                st.write(f"{i + 1}. {entry.original_phrase} → {names[match['ingredient_id']]}")
            else:
                suggestions = match["suggestions"]
                choices = suggestions if match["status"] == "AMBIGUOUS" else list(dict.fromkeys(suggestions + ingredient_options))
                default = choices.index(entry.ingredient_id) if entry.ingredient_id in choices else None
                selected = st.selectbox(f"Match line {i + 1}: {entry.original_phrase}", choices, index=default,
                                        placeholder="Choose the ingredient you meant", format_func=names.get, key="map_" + widget_id)
                if selected:
                    confirmations[i] = selected
            essential = st.checkbox(f"Essential ingredient on line {i + 1}", value=entry.essential, key="essential_" + widget_id)
            entries.append(entry.model_copy(update={"essential": essential}))
        if st.button("Save custom recipe", type="primary"):
            try:
                confirmed = confirm_custom_recipe(draft.model_copy(update={"ingredients": entries}), catalog, confirmations)
                state["custom_recipes"][str(confirmed.recipe_id)] = confirmed
                del state["draft_recipe"]
                st.success(f"Saved {confirmed.title} in this session.")
            except ValueError as error:
                st.error(str(error))
    st.markdown("### 📚 Your saved recipes")

    for key, saved in state["custom_recipes"].items():
        with st.container(border=True):
            st.subheader(f"🍲 {saved.title}")
            st.caption(f"{len(saved.ingredients)} ingredient entries · {len(saved.instructions)} instruction steps")
            st.button("Use this recipe for substitution", key="use_" + key, on_click=open_recipe, args=(key,))
            st.download_button("Download recipe JSON", export_custom_recipe(saved), file_name=f"recipe-{key}.json",
                               mime="application/json", key="download_" + key)



# ===== HERO HEADER =====

hero_left, hero_right = st.columns([3, 1])

with hero_left:
    st.markdown("""
    <div class="kc-hero">
        <div class="kc-eyebrow">
            YOUR SMART COOKING COMPANION
        </div>
        <div class="kc-hero-title">
            KitchenCompass
        </div>
        <div class="kc-hero-subtitle">
            Discover recipes. Make the most of your ingredients.
            Cook with confidence.
        </div>
    </div>
    """, unsafe_allow_html=True)

with hero_right:
    st.markdown("""
    <div class="kc-hero">
        <div class="kc-hero-art">🍲</div>
        <div style="text-align:center; color:#204B37;
                    font-weight:700;">
            Discover • Substitute • Cook
        </div>
    </div>
    """, unsafe_allow_html=True)


# ===== SIDEBAR BRANDING =====

st.sidebar.markdown("""
<div class="kc-sidebar-brand">🍃 KitchenCompass</div>
<div class="kc-sidebar-tagline">
    Discover • Substitute • Cook
</div>
<div class="kc-sidebar-divider"></div>
""", unsafe_allow_html=True)

page = st.sidebar.radio(
    "EXPLORE KITCHENCOMPASS",
    [
        "Pantry search",
        "Substitutions",
        "Joint replacements",
        "Custom recipes"
    ],
    key="workspace"
)

st.sidebar.markdown(
    '<div class="kc-sidebar-divider"></div>',
    unsafe_allow_html=True
)

st.sidebar.markdown(
    f"🍲 **{len(catalog.recipes)}** recipes",
    unsafe_allow_html=True
)

st.sidebar.markdown(
    f"🌿 **{len(names)}** ingredients",
    unsafe_allow_html=True
)

st.sidebar.markdown(
    '<div class="kc-sidebar-divider"></div>',
    unsafe_allow_html=True
)

st.sidebar.caption(
    f"Data {catalog.config['data_version']} · "
    f"Model {catalog.config['config_version']}"
)


# ===== PAGE ROUTING =====

if page == "Pantry search":
    pantry_page()
elif page == "Substitutions":
    substitute_page()
elif page == "Joint replacements":
    joint_page()
else:
    custom_page()
