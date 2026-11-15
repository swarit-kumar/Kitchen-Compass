"""Data contracts shared by catalogue preparation and application services."""
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

SchemaVersion = Literal["1.0"]
NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Role = Literal["fat", "acid", "sweetener", "thickener", "aromatic", "bulk", "protein", "liquid"]
Family = Literal["curry", "soup", "other"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Ingredient(Contract):
    ingredient_id: NonEmpty
    display_name: NonEmpty
    aliases: list[NonEmpty]
    category: NonEmpty
    default_roles: list[Role]
    components: list[NonEmpty]
    source_refs: list[NonEmpty] = Field(min_length=1)
    schema_version: SchemaVersion


class RecipeIngredient(Contract):
    ingredient_id: NonEmpty
    original_phrase: NonEmpty
    quantity_text: NonEmpty | None
    essential: bool
    essential_reason: NonEmpty | None

    @model_validator(mode="after")
    def check_essential_reason(self):
        if self.essential != (self.essential_reason is not None):
            raise ValueError("essential ingredients require a reason; other entries use null")
        return self


class Recipe(Contract):
    recipe_id: NonEmpty
    title: NonEmpty
    dish_family: Family
    ingredients: list[RecipeIngredient] = Field(min_length=2, max_length=30)
    instructions: list[NonEmpty] = Field(min_length=1)
    source_ref: NonEmpty
    duplicate_group_id: NonEmpty
    schema_version: SchemaVersion


class RawIngredient(Contract):
    original_phrase: NonEmpty
    ingredient_name_hint: NonEmpty
    quantity_text: NonEmpty | None
    compound_review_required: bool


class RawRecipe(Contract):
    recipe_id: NonEmpty
    title: NonEmpty
    cuisine_label: NonEmpty
    dish_family: Family
    ingredients: list[RawIngredient] = Field(min_length=2, max_length=30)
    instructions: list[NonEmpty] = Field(min_length=1)
    source_ref: NonEmpty


class Source(Contract):
    source_id: NonEmpty
    title: NonEmpty
    url: NonEmpty | None = None
    local_filename: NonEmpty | None = None
    accessed_date: NonEmpty
    locator: NonEmpty
    license_status: NonEmpty
    permitted_uses: list[NonEmpty] = Field(min_length=1)

    @model_validator(mode="after")
    def check_location(self):
        if not (self.url or self.local_filename):
            raise ValueError("source must identify a URL or local file")
        return self


class FlavorProfile(Contract):
    ingredient_id: NonEmpty
    compound_ids: list[Annotated[str, StringConstraints(pattern=r"^pubchem:[1-9][0-9]*$")]]
    evidence_status: Literal["available", "missing"]
    source_refs: list[NonEmpty]

    @model_validator(mode="after")
    def check_evidence(self):
        if self.evidence_status == "available" and not (self.compound_ids and self.source_refs):
            raise ValueError("available evidence requires compound IDs and provenance")
        if self.evidence_status == "missing" and self.compound_ids:
            raise ValueError("missing evidence cannot contain compounds")
        if self.compound_ids != sorted(set(self.compound_ids)):
            raise ValueError("compound IDs must be sorted and unique")
        return self


class RoleRule(Contract):
    rule_id: NonEmpty
    ingredient_ids: list[NonEmpty] = Field(min_length=1)
    categories: list[NonEmpty]
    action_keywords: list[NonEmpty] = Field(min_length=1)
    role: Role
    priority: int = Field(ge=0)
    source_refs: list[NonEmpty] = Field(min_length=1)


class Constraints(Contract):
    pantry_ids: list[NonEmpty] = Field(default_factory=list)
    excluded_ids: list[NonEmpty] = Field(default_factory=list)
    pantry_only: bool = False
    max_replacements: int = Field(default=3, ge=1, le=3)


class Result(Contract):
    status: Literal["OK", "NEEDS_INPUT", "UNSUPPORTED_INPUT", "UNRESOLVED_EXCLUSION", "NO_FEASIBLE_RESULT"]
    items: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reason_counts: dict[str, Annotated[int, Field(ge=0)]] = Field(default_factory=dict)
    schema_version: SchemaVersion = "1.0"
    data_version: str = "not-created"
    config_version: str = "not-created"
