from typing import Any

import pytest

from nda.label_transformer import (
    label_schema_to_string,
    parse_label_to_schema,
    sort_label_fields,
)


class TestSortLabelFields:
    @pytest.fixture
    def label(self):
        return "effective_date=2017-02-10 jurisdiction=California party=Kite_Pharma_Inc. party=Gilead_Sciences_Inc. term=7_years"

    @pytest.fixture
    def expected(self):
        return "effective_date=2017-02-10 jurisdiction=California party=Kite_Pharma_Inc. party=Gilead_Sciences_Inc. term=7_years"

    def test_already_sorted_is_unchanged(self, label):
        """When the input is already in the right order, output equals input."""
        assert sort_label_fields(string=label) == label

    def test_reorders_out_of_order_keys(self, label, expected):
        """Keys that appear in the wrong order get moved to their canonical position."""
        assert sort_label_fields(string=label) == expected

    def test_multiple_party_entries_are_preserved(self):
        """Multiple party= tokens should all appear together after jurisdiction."""
        label = "party=Alice party=Bob effective_date=2020-01-01"
        result = sort_label_fields(string=label)
        assert result == "effective_date=2020-01-01 party=Alice party=Bob"

    def test_unknown_keys_are_appended_at_end(self):
        """Keys not in the schema are kept but moved to the end."""
        label = "foo=bar effective_date=2020-01-01"
        result = sort_label_fields(string=label)
        assert result.startswith("effective_date=2020-01-01")
        assert result.endswith("foo=bar")

    def test_single_token(self):
        """A single token returns that token unchanged."""
        assert sort_label_fields(string="term=1_year") == "term=1_year"


class TestParseLabelToSchema:
    def test_full_label_round_trips(self):
        """A fully-populated label produces a dict with all four keys."""
        label = (
            "effective_date=2020-01-01 jurisdiction=California party=Acme term=2_years"
        )
        result = parse_label_to_schema(label)
        assert result["effective_date"] == "2020-01-01"
        assert result["jurisdiction"] == "California"
        assert result["term"] == "2_years"
        assert result["party"] == [{"name": "Acme"}]

    def test_missing_optional_fields_are_none(self):
        """Fields absent from the label string come back as None (not missing keys)."""
        result = parse_label_to_schema("party=Acme")
        assert result["effective_date"] is None
        assert result["jurisdiction"] is None
        assert result["term"] is None

    def test_multiple_parties_are_collected(self):
        """Each party= token becomes a separate dict in the list."""
        result = parse_label_to_schema("party=Alice party=Bob")
        assert result["party"] == [{"name": "Alice"}, {"name": "Bob"}]

    def test_unknown_key_is_ignored_by_schema(self):
        """Keys not defined in NDA are silently discarded by the Pydantic model."""
        result = parse_label_to_schema("decoy=value effective_date=2021-06-01")
        assert result["effective_date"] == "2021-06-01"
        assert "decoy" not in result

    def test_returns_dict(self):
        """Return type is always a plain dict (required for DataFrame storage)."""
        result = parse_label_to_schema("term=1_year")
        assert isinstance(result, dict)


class TestLabelSchemaToString:
    def test_full_schema_serializes_correctly(self) -> None:
        nda_dict: dict[str, Any] = {
            "effective_date": "2020-01-01",
            "jurisdiction": "California",
            "party": [{"name": "Acme"}],
            "term": "2_years",
        }
        result = label_schema_to_string(nda_dict)
        assert (
            result
            == "effective_date=2020-01-01 jurisdiction=California party=Acme term=2_years"
        )

    def test_none_values_are_omitted(self) -> None:
        """None fields must not appear in the serialized output."""
        nda_dict: dict[str, Any] = {
            "effective_date": None,
            "jurisdiction": "Delaware",
            "party": [],
            "term": None,
        }
        result = label_schema_to_string(nda_dict)
        assert result == "jurisdiction=Delaware"

    def test_empty_schema_is_empty_string(self) -> None:
        nda_dict: dict[str, Any] = {
            "effective_date": None,
            "jurisdiction": None,
            "party": [],
            "term": None,
        }
        assert label_schema_to_string(nda_dict) == ""

    def test_multiple_parties_serialize_as_separate_tokens(self) -> None:
        nda_dict: dict[str, Any] = {
            "effective_date": None,
            "jurisdiction": None,
            "party": [{"name": "Alice"}, {"name": "Bob"}],
            "term": None,
        }
        result = label_schema_to_string(nda_dict)
        assert result == "party=Alice party=Bob"


class TestRoundTrip:
    @pytest.mark.parametrize(
        "label",
        [
            "effective_date=2020-01-01 jurisdiction=California party=Acme term=2_years",
            "party=Alice party=Bob",
            "jurisdiction=Delaware",
            "term=11_months",
        ],
    )
    def test_parse_then_serialize_is_stable(self, label: str) -> None:
        """
        pytest.mark.parametrize lets you run the same test with many
        different inputs without copy-pasting the function.
        """
        first_pass = label_schema_to_string(parse_label_to_schema(label))
        second_pass = label_schema_to_string(parse_label_to_schema(first_pass))
        assert first_pass == second_pass
