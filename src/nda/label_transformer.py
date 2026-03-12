"""
Label transformation pipeline from raw TSV strings to structured NDA schema records.
"""

from collections import defaultdict
from typing import Any

import pandas as pd

from nda.data_loader import Partition
from nda.schema import NDA, Party


def transform(df: pd.DataFrame, partition: Partition) -> pd.DataFrame:
    """
    Add three label columns forming a round-trip validation pipeline.

    - `labels_canonical`: raw labels reordered to the fixed NDA schema field order.
    - `labels_schema`: canonical parsed through the Pydantic NDA model, yielding
      the effective ground truth, stored as dict for DataFrame compatibility.
    - `labels_serialized`: schema serialised back to key=value; canonical == serialized
      confirms consistent parsing and correct exclusion of decoy keys.
    """
    if partition == "test-A":
        return df
    return (
        df.assign(labels_canonical=lambda df: df.labels.apply(sort_label_fields))
        .assign(
            labels_schema=lambda df: df.labels_canonical.apply(parse_label_to_schema)
        )
        .assign(
            labels_serialized=lambda df: df.labels_schema.apply(label_schema_to_string)
        )
    )


def sort_label_fields(string: str) -> str:
    """
    Reorder key=value pairs to match the canonical NDA schema field order.
    """
    schema_order = ["effective_date", "jurisdiction", "party", "term"]

    pairs: list[tuple[str, str]] = []
    for part in string.strip().split():
        key, value = part.split("=", 1)
        pairs.append((key, value))

    grouped: dict[str, list[str]] = {k: [] for k in schema_order}
    others: list[str] = []
    for key, value in pairs:
        if key in grouped:
            grouped[key].append(f"{key}={value}")
        else:
            others.append(f"{key}={value}")

    result: list[str] = []
    for key in schema_order:
        result.extend(grouped[key])
    result.extend(others)
    return " ".join(result)


def parse_label_to_schema(string: str) -> dict[str, Any]:
    """
    Parse a raw label string into a validated NDA model dictionary.
    """
    result: defaultdict[str, list[str]] = defaultdict(list)

    for token in string.strip().split():
        key, _, value = token.partition("=")
        result[key].append(value)

    effective_date = result.get("effective_date", [None])[0]
    jurisdiction = result.get("jurisdiction", [None])[0]
    term = result.get("term", [None])[0]
    parties = result.get("party", [])
    party = [Party(name=p) for p in parties]

    nda = NDA(
        effective_date=effective_date,
        jurisdiction=jurisdiction,
        term=term,
        party=party,
    )

    return nda.model_dump()


def label_schema_to_string(nda_dict: dict[str, Any]) -> str:
    """
    Serialise an NDA model dictionary back to a normalised key=value label string.
    """
    parts: list[str] = []

    for key in ["effective_date", "jurisdiction"]:
        value = nda_dict.get(key)
        if value is not None:
            parts.append(f"{key}={value}")

    for party in nda_dict.get("party", []):
        parts.append(f"party={party['name']}")

    term = nda_dict.get("term")
    if term is not None:
        parts.append(f"term={term}")

    return " ".join(parts)
