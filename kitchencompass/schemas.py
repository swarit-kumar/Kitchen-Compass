
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Result(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal[
        "OK",
        "NEEDS_INPUT",
        "UNSUPPORTED_INPUT",
        "UNRESOLVED_EXCLUSION",
        "NO_FEASIBLE_RESULT",
    ]

    items: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reason_counts: dict[str, int] = Field(default_factory=dict)

    schema_version: str = "1.0"
    data_version: str = "not-created"
    config_version: str = "not-created"
