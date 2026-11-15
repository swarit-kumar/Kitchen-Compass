
"""Ingredient exclusion and recipe constraint handling."""

from collections import defaultdict


class ConstraintEngine:
    """Apply ingredient exclusions using nested component relationships."""

    def __init__(self, ingredients):
        self.ingredients = {
            item["ingredient_id"]: item for item in ingredients
        }

        # Build reverse relationships:
        # milk -> butter -> ghee
        self.used_in = defaultdict(set)

        for ingredient_id, ingredient in self.ingredients.items():
            for component_id in ingredient.get("components", []):
                if component_id not in self.ingredients:
                    raise ValueError(
                        f"Unknown component ID {component_id} "
                        f"referenced by {ingredient_id}"
                    )

                self.used_in[component_id].add(ingredient_id)

    def expand_exclusions(self, excluded_ids):
        """Include every ingredient that contains an excluded component."""
        expanded = set()
        pending = list(excluded_ids)

        while pending:
            ingredient_id = pending.pop()

            if ingredient_id not in self.ingredients:
                raise ValueError(
                    f"Unknown excluded ingredient ID: {ingredient_id}"
                )

            if ingredient_id in expanded:
                continue

            expanded.add(ingredient_id)

            # Find compounds that use this ingredient as a component.
            pending.extend(sorted(self.used_in[ingredient_id] - expanded))

        return sorted(expanded)

    def recipe_is_allowed(self, recipe, excluded_ids):
        """Return False if a recipe contains an excluded ingredient."""
        expanded = set(self.expand_exclusions(excluded_ids))

        recipe_ids = {
            item["ingredient_id"] for item in recipe["ingredients"]
        }

        return not bool(recipe_ids & expanded)

    def filter_recipes(self, recipes, excluded_ids):
        """Return eligible recipes and the expanded exclusion list."""
        expanded = self.expand_exclusions(excluded_ids)
        excluded_set = set(expanded)

        eligible = []

        for recipe in recipes:
            recipe_ids = {
                item["ingredient_id"]
                for item in recipe["ingredients"]
            }

            if not recipe_ids & excluded_set:
                eligible.append(recipe)

        return eligible, expanded
