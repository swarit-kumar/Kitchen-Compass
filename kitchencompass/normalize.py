
"""Ingredient name and alias normalization."""

import json
import re
from collections import defaultdict
from pathlib import Path


def normalize_text(value: str) -> str:
    """Normalize whitespace and capitalization for name matching."""
    return re.sub(r"\s+", " ", value.strip().lower())


class IngredientNormalizer:
    """Resolve ingredient names and IDs using the processed catalogue."""

    def __init__(self, ingredients):
        self.ingredients = {
            item["ingredient_id"]: item for item in ingredients
        }

        self.name_to_ids = defaultdict(set)

        for ingredient_id, item in self.ingredients.items():
            names = [
                item["display_name"],
                *item.get("aliases", []),
                ingredient_id,
            ]

            for name in names:
                self.name_to_ids[normalize_text(name)].add(ingredient_id)

    @classmethod
    def from_file(cls, path="data/processed/ingredients.jsonl"):
        path = Path(path)

        with path.open(encoding="utf-8-sig") as file:
            ingredients = [
                json.loads(line)
                for line in file
                if line.strip()
            ]

        return cls(ingredients)

    def resolve(self, value: str) -> dict:
        """Resolve a name or return suggestions for confirmation."""
        name = normalize_text(value)

        if not name:
            return {
                "status": "UNRESOLVED",
                "ingredient_id": None,
                "suggestions": [],
            }

        matches = self.name_to_ids.get(name, set())

        if len(matches) == 1:
            return {
                "status": "RESOLVED",
                "ingredient_id": next(iter(matches)),
                "suggestions": [],
            }

        if len(matches) > 1:
            return {
                "status": "AMBIGUOUS",
                "ingredient_id": None,
                "suggestions": sorted(matches),
            }

        # Suggest names sharing words with the unknown input.
        input_words = set(name.split())

        ranked = []
        for ingredient_id, item in self.ingredients.items():
            names = [
                item["display_name"],
                *item.get("aliases", []),
            ]
            score = max(
                (
                    len(input_words & set(normalize_text(candidate).split()))
                    for candidate in names
                ),
                default=0,
            )
            if score:
                ranked.append((score, ingredient_id))

        ranked.sort(key=lambda entry: (-entry[0], entry[1]))

        return {
            "status": "UNRESOLVED",
            "ingredient_id": None,
            "suggestions": [
                ingredient_id for _, ingredient_id in ranked[:5]
            ],
        }
