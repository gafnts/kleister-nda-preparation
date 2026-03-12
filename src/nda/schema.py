"""
Pydantic models defining the canonical NDA extraction schema.
"""

import re
from datetime import date

from pydantic import BaseModel, Field, field_validator


class Party(BaseModel):
    name: str = Field(..., description="Name of one party involved in the contract.")

    @field_validator("name", mode="before")
    @classmethod
    def normalize_underscores(cls, v: str) -> str:
        return v.replace(" ", "_").replace(":", "_")


class NDA(BaseModel):
    """
    * In attribute values, all spaces ` ` and colons `:` should be replaced with an underscore `_`
    * The effective date should be returned in `YYYY-MM-DD` format
    * Values for the attribute `term` should be normalized with the same original units, for example:
        * `eleven months` is changed to `11_months`;
        * all of them should be in the same format: `{number}_{units}`
    """

    effective_date: str | None = Field(
        None,
        description="Date in `YYYY-MM-DD` format, at which point the contract is legally binding.",
    )
    jurisdiction: str | None = Field(
        None,
        description="Under which state _or_ country jurisdiction is the contract signed.",
    )
    party: list[Party] = Field(
        default_factory=list, description="Party or parties involved in the contract."
    )
    term: str | None = Field(
        None, description="Length of the legal contract as expressed in the document."
    )

    @field_validator("effective_date", mode="before")
    @classmethod
    def validate_effective_date(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError(
                f"effective_date must be in YYYY-MM-DD format, got '{v}'"
            ) from None
        return v

    @field_validator("jurisdiction", "term", mode="before")
    @classmethod
    def normalize_underscores(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.replace(" ", "_").replace(":", "_")

    @field_validator("term", mode="after")
    @classmethod
    def validate_term_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not re.fullmatch(r"\d+(?:\.\d+)?_\w+", v):
            raise ValueError(
                f"term must be in '{{number}}_{{units}}' format, got '{v}'"
            ) from None
        return v
