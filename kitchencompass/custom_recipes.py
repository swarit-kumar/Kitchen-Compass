
"""Custom recipe validation and JSON import/export."""

from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    model_validator,
)


MAX_IMPORT_SIZE = 1_048_576

RecipeTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
]

IngredientPhrase = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]

InstructionStep = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2000),
]


class CustomIngredient(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    original_phrase: IngredientPhrase
    quantity_text: str | None = None
    ingredient_id: IngredientPhrase | None = None
    essential: bool = False


class CustomRecipe(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    recipe_id: UUID = Field(default_factory=uuid4)
    title: RecipeTitle
    ingredients: list[CustomIngredient] = Field(
        min_length=2,
        max_length=30,
    )
    instructions: list[InstructionStep] = Field(
        default_factory=list,
        max_length=30,
    )
    instructions_not_provided: bool = False
    schema_version: Literal["2.0"] = "2.0"

    @model_validator(mode="before")
    @classmethod
    def upgrade_legacy_json(cls, value, info: ValidationInfo):
        if isinstance(value, dict):
            if info.context and info.context.get("imported") and "schema_version" not in value:
                raise ValueError("A recipe JSON file must specify schema_version.")
            if value.get("schema_version") == "1.0":
                return {**value, "schema_version": "2.0"}
        return value

    @model_validator(mode="after")
    def validate_instructions(self):
        if not self.instructions and not self.instructions_not_provided:
            raise ValueError(
                "Provide at least one instruction or explicitly mark "
                "instructions as not provided."
            )

        if self.instructions and self.instructions_not_provided:
            raise ValueError(
                "Do not provide instructions when marked as not provided."
            )

        return self


def create_custom_recipe(
    title,
    ingredients,
    instructions=None,
    instructions_not_provided=False,
):
    """Create and validate a custom recipe with a new UUID."""

    return CustomRecipe(
        recipe_id=uuid4(),
        title=title,
        ingredients=ingredients,
        instructions=instructions or [],
        instructions_not_provided=instructions_not_provided,
    )


def export_custom_recipe(recipe):
    """Export one validated custom recipe as schema-versioned JSON."""

    if not isinstance(recipe, CustomRecipe):
        recipe = CustomRecipe.model_validate(recipe)

    payload = recipe.model_dump_json(indent=2)

    if len(payload.encode("utf-8")) > MAX_IMPORT_SIZE:
        raise ValueError("Recipe export exceeds the 1 MB limit.")

    return payload


def import_custom_recipe(payload):
    """Import and validate a custom recipe from JSON."""

    if isinstance(payload, bytes):
        if len(payload) > MAX_IMPORT_SIZE:
            raise ValueError("JSON upload exceeds the 1 MB limit.")
        payload = payload.decode("utf-8")

    elif isinstance(payload, str):
        if len(payload.encode("utf-8")) > MAX_IMPORT_SIZE:
            raise ValueError("JSON upload exceeds the 1 MB limit.")

    else:
        raise TypeError("Import must contain JSON text or bytes.")

    return CustomRecipe.model_validate_json(payload, context={"imported": True})
