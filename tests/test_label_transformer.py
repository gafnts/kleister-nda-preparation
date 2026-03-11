"""
Tests for label_transformer.py
(sort_label_fields, parse_label_to_schema, label_schema_to_string, transform)
"""

from typing import Any

import pandas as pd
import pytest

from nda.label_transformer import (
    label_schema_to_string,
    parse_label_to_schema,
    sort_label_fields,
    transform,
)


class TestSortLabelFields:
    def test_already_canonical_order_unchanged(self) -> None:
        raw = (
            "effective_date=2020-01-01 jurisdiction=California party=Acme term=2_years"
        )
        assert sort_label_fields(raw) == raw

    def test_reorders_to_schema_order(self) -> None:
        raw = (
            "term=2_years party=Acme effective_date=2020-01-01 jurisdiction=California"
        )
        expected = (
            "effective_date=2020-01-01 jurisdiction=California party=Acme term=2_years"
        )
        assert sort_label_fields(raw) == expected

    def test_multiple_parties_stay_grouped(self) -> None:
        raw = "party=Acme term=1_year party=Globex"
        result = sort_label_fields(raw)
        assert result == "party=Acme party=Globex term=1_year"

    def test_unknown_keys_appended_at_end(self) -> None:
        raw = "decoy=noise effective_date=2020-01-01"
        result = sort_label_fields(raw)
        assert result == "effective_date=2020-01-01 decoy=noise"

    def test_strips_surrounding_whitespace(self) -> None:
        raw = "  term=1_year  "
        assert sort_label_fields(raw) == "term=1_year"

    def test_empty_string_returns_empty(self) -> None:
        assert sort_label_fields("") == ""


class TestParseLabelToSchema:
    def test_all_fields_populated(self) -> None:
        raw = (
            "effective_date=2020-01-01 jurisdiction=California party=Acme term=2_years"
        )
        result = parse_label_to_schema(raw)
        assert result["effective_date"] == "2020-01-01"
        assert result["jurisdiction"] == "California"
        assert result["party"] == [{"name": "Acme"}]
        assert result["term"] == "2_years"

    def test_missing_fields_default_to_none(self) -> None:
        result = parse_label_to_schema("party=Acme")
        assert result["effective_date"] is None
        assert result["jurisdiction"] is None
        assert result["term"] is None

    def test_multiple_parties(self) -> None:
        result = parse_label_to_schema("party=Acme party=Globex")
        assert result["party"] == [{"name": "Acme"}, {"name": "Globex"}]

    def test_no_parties_yields_empty_list(self) -> None:
        result = parse_label_to_schema("term=1_year")
        assert result["party"] == []

    def test_decoy_keys_discarded(self) -> None:
        result = parse_label_to_schema("decoy=noise party=Acme")
        assert "decoy" not in result

    def test_space_in_party_value_splits_into_separate_tokens(self) -> None:
        result = parse_label_to_schema("party=MPB Corp")
        # whitespace-delimited format truncates at the space;
        # only "MPB" survives as the party name
        assert result["party"][0]["name"] == "MPB"

    def test_returns_dict_not_model(self) -> None:
        result = parse_label_to_schema("term=1_year")
        assert isinstance(result, dict)


class TestLabelSchemaToString:
    def test_full_schema_serializes_in_order(self) -> None:
        nda_dict: dict[str, Any] = {
            "effective_date": "2020-01-01",
            "jurisdiction": "California",
            "party": [{"name": "Acme"}],
            "term": "2_years",
        }
        expected = (
            "effective_date=2020-01-01 jurisdiction=California party=Acme term=2_years"
        )
        assert label_schema_to_string(nda_dict) == expected

    def test_none_fields_omitted(self) -> None:
        nda_dict: dict[str, Any] = {
            "effective_date": None,
            "jurisdiction": None,
            "party": [],
            "term": None,
        }
        assert label_schema_to_string(nda_dict) == ""

    def test_multiple_parties_serialized(self) -> None:
        nda_dict: dict[str, Any] = {
            "effective_date": None,
            "jurisdiction": None,
            "party": [{"name": "Acme"}, {"name": "Globex"}],
            "term": None,
        }
        assert label_schema_to_string(nda_dict) == "party=Acme party=Globex"

    def test_parties_appear_between_jurisdiction_and_term(self) -> None:
        nda_dict: dict[str, Any] = {
            "effective_date": None,
            "jurisdiction": "California",
            "party": [{"name": "Acme"}],
            "term": "1_year",
        }
        result = label_schema_to_string(nda_dict)
        assert result == "jurisdiction=California party=Acme term=1_year"


class TestRoundTrip:
    @pytest.mark.parametrize(
        "raw",
        [
            "effective_date=2020-01-01 jurisdiction=California party=Acme term=2_years",
            "party=Acme party=Globex",
            "term=11_months",
            "jurisdiction=New_York party=Acme",
        ],
    )
    def test_canonical_survives_parse_and_serialize(self, raw: str) -> None:
        canonical = sort_label_fields(raw)
        schema = parse_label_to_schema(canonical)
        serialized = label_schema_to_string(schema)
        assert serialized == canonical

    def test_decoy_keys_dropped_on_round_trip(self) -> None:
        raw = "effective_date=2020-01-01 decoy=noise party=Acme"
        canonical = sort_label_fields(raw)
        schema = parse_label_to_schema(canonical)
        serialized = label_schema_to_string(schema)
        assert "decoy" not in serialized


class TestTransform:
    def test_adds_three_columns(self) -> None:
        df = pd.DataFrame({"filename": ["a.pdf"], "labels": ["party=Acme term=1_year"]})
        result = transform(df, "train")
        assert "labels_canonical" in result.columns
        assert "labels_schema" in result.columns
        assert "labels_serialized" in result.columns

    def test_original_columns_preserved(self) -> None:
        df = pd.DataFrame({"filename": ["a.pdf"], "labels": ["party=Acme term=1_year"]})
        result = transform(df, "train")
        assert "filename" in result.columns
        assert "labels" in result.columns

    def test_test_a_returns_dataframe_unchanged(self) -> None:
        df = pd.DataFrame({"filename": ["a.pdf"]})
        result = transform(df, "test-A")
        pd.testing.assert_frame_equal(result, df)

    def test_dev_partition_processes_labels(self) -> None:
        df = pd.DataFrame({"filename": ["a.pdf"], "labels": ["party=Acme"]})
        result = transform(df, "dev-0")
        assert "labels_schema" in result.columns

    def test_canonical_equals_serialized_confirms_consistency(self) -> None:
        df = pd.DataFrame(
            {
                "filename": ["a.pdf"],
                "labels": ["effective_date=2020-01-01 party=Acme term=2_years"],
            }
        )
        result = transform(df, "train")
        assert result["labels_canonical"].iloc[0] == result["labels_serialized"].iloc[0]
