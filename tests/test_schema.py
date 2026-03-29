"""
Tests for schema.py
(Pydantic models: Party, NDA)
"""

from typing import cast

import pytest
from pydantic import ValidationError

from nda.schema import NDA, Party


@pytest.fixture
def empty_nda() -> NDA:
    """Return an empty, valid NDA instance."""
    return NDA()


@pytest.fixture
def full_nda() -> NDA:
    """Return a fully-populated, valid NDA instance."""
    return NDA(
        effective_date="2020-01-01",
        jurisdiction="California",
        party=[Party(name="MPB_Corp"), Party(name="Gadget_Ltd")],
        term="2_years",
    )


class TestParty:
    def test_name_is_required(self) -> None:
        with pytest.raises(ValidationError):
            Party()  # type: ignore[call-arg]

    def test_valid_party(self) -> None:
        p = Party(name="MPB_Corp")
        assert p.name == "MPB_Corp"

    def test_spaces_become_underscores(self) -> None:
        p = Party(name="MPB Corp")
        assert p.name == "MPB_Corp"

    def test_colons_become_underscores(self) -> None:
        p = Party(name="Corp:LLC")
        assert p.name == "Corp_LLC"

    def test_already_clean_value_unchanged(self) -> None:
        p = Party(name="Acme")
        assert p.name == "Acme"

    def test_commas_are_stripped(self) -> None:
        p = Party(name="Acme, Inc.")
        assert p.name == "Acme_Inc."

    def test_curly_single_quotes_normalized(self) -> None:
        p = Party(name="O\u2019Brien\u2018s")
        assert p.name == "O'Brien's"

    def test_curly_double_quotes_normalized(self) -> None:
        p = Party(name="\u201cAcme\u201d")
        assert p.name == '"Acme"'


class TestEffectiveDate:
    def test_defaults_to_none(self) -> None:
        nda = NDA()
        assert nda.effective_date is None

    def test_none_is_allowed(self) -> None:
        nda = NDA(effective_date=None)
        assert nda.effective_date is None

    def test_valid_date(self) -> None:
        nda = NDA(effective_date="2020-01-15")
        assert nda.effective_date == "2020-01-15"

    def test_rejects_non_date_string(self) -> None:
        with pytest.raises(ValidationError, match="YYYY-MM-DD"):
            NDA(effective_date="not-a-date")

    def test_rejects_empty_string(self) -> None:
        with pytest.raises(ValidationError, match="YYYY-MM-DD"):
            NDA(effective_date="")

    def test_rejects_wrong_separator(self) -> None:
        with pytest.raises(ValidationError, match="YYYY-MM-DD"):
            NDA(effective_date="2020/01/15")


class TestJurisdiction:
    def test_defaults_to_none(self) -> None:
        nda = NDA()
        assert nda.jurisdiction is None

    def test_none_is_allowed(self) -> None:
        nda = NDA(jurisdiction=None)
        assert nda.jurisdiction is None

    def test_spaces_become_underscores(self) -> None:
        nda = NDA(jurisdiction="New York")
        assert nda.jurisdiction == "New_York"

    def test_colons_become_underscores(self) -> None:
        nda = NDA(jurisdiction="Region:East")
        assert nda.jurisdiction == "Region_East"

    def test_already_clean_value_unchanged(self) -> None:
        nda = NDA(jurisdiction="California")
        assert nda.jurisdiction == "California"

    def test_state_of_prefix_stripped(self) -> None:
        nda = NDA(jurisdiction="State of New York")
        assert nda.jurisdiction == "New_York"

    def test_commonwealth_of_prefix_stripped(self) -> None:
        nda = NDA(jurisdiction="Commonwealth of Virginia")
        assert nda.jurisdiction == "Virginia"

    def test_no_prefix_left_unchanged(self) -> None:
        nda = NDA(jurisdiction="Delaware")
        assert nda.jurisdiction == "Delaware"


class TestTerm:
    def test_defaults_to_none(self) -> None:
        nda = NDA()
        assert nda.term is None

    def test_none_is_allowed(self) -> None:
        nda = NDA(term=None)
        assert nda.term is None

    def test_valid_term(self) -> None:
        nda = NDA(term="11_months")
        assert nda.term == "11_months"

    def test_spaces_normalized_before_format_check(self) -> None:
        nda = NDA(term="2 years")
        assert nda.term == "2_years"

    def test_colons_normalized(self) -> None:
        nda = NDA(term="2:years")
        assert nda.term == "2_years"

    def test_rejects_plain_text(self) -> None:
        with pytest.raises(ValidationError, match="number.*units"):
            NDA(term="forever")

    def test_rejects_units_without_number(self) -> None:
        with pytest.raises(ValidationError, match="number.*units"):
            NDA(term="years")


class TestPartyField:
    def test_defaults_to_empty_list(self) -> None:
        nda = NDA()
        assert nda.party == []

    def test_accepts_raw_dicts(self) -> None:
        nda = NDA(party=cast(list[Party], [{"name": "Acme"}]))
        assert isinstance(nda.party[0], Party)
        assert nda.party[0].name == "Acme"

    def test_rejects_dict_without_name(self) -> None:
        with pytest.raises(ValidationError):
            NDA(party=cast(list[Party], [{}]))


class TestNDASerialization:
    def test_full_nda_round_trips_through_dump(self, full_nda: NDA) -> None:
        data = full_nda.model_dump()
        reconstructed = NDA(**data)
        assert reconstructed == full_nda

    def test_empty_nda_dump(self, empty_nda: NDA) -> None:
        assert empty_nda.model_dump() == {
            "effective_date": None,
            "jurisdiction": None,
            "party": [],
            "term": None,
        }
