"""
Tests for schema.py  (Pydantic models: Party, NDA)

New concepts introduced here:
  - pytest.raises  — assert that code raises a specific exception
  - fixtures       — reusable setup objects shared across tests
"""

import pytest
from pydantic import ValidationError

from nda.schema import NDA, Party

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
# A fixture is a function decorated with @pytest.fixture.
# pytest automatically calls it and injects the return value into any test
# that lists the fixture name as a parameter.  Think of it as a
# "reusable test helper" that runs fresh for every test.


@pytest.fixture
def full_nda() -> NDA:
    """Return a fully-populated, valid NDA instance."""
    return NDA(
        effective_date="2020-01-01",
        jurisdiction="California",
        party=[Party(name="Acme Corp"), Party(name="Widget Ltd")],
        term="2_years",
    )


@pytest.fixture
def empty_nda() -> NDA:
    """Return an NDA where all optional fields are omitted (defaults apply)."""
    return NDA()


# ---------------------------------------------------------------------------
# Party model
# ---------------------------------------------------------------------------


class TestParty:
    def test_name_is_required(self):
        """
        pytest.raises is a context manager that ASSERTS an exception is raised.
        If the code inside `with` does NOT raise ValidationError, the test fails.
        This is how you test that invalid input is rejected.
        """
        with pytest.raises(ValidationError):
            Party()  # type: ignore[call-arg]  # name is required — no default

    def test_valid_party(self):
        p = Party(name="Acme Corp")
        assert p.name == "Acme Corp"

    def test_model_dump_returns_dict(self):
        p = Party(name="Acme")
        assert p.model_dump() == {"name": "Acme"}


# ---------------------------------------------------------------------------
# NDA model — construction
# ---------------------------------------------------------------------------


class TestNDAConstruction:
    def test_all_fields_optional_except_party_list(self, empty_nda: NDA) -> None:
        """
        Note the `empty_nda` parameter — pytest looks for the fixture with
        that name and injects it automatically. No need to call it yourself.
        """
        assert empty_nda.effective_date is None
        assert empty_nda.jurisdiction is None
        assert empty_nda.term is None
        assert empty_nda.party == []  # default_factory gives an empty list

    def test_full_construction(self, full_nda: NDA) -> None:
        assert full_nda.effective_date == "2020-01-01"
        assert full_nda.jurisdiction == "California"
        assert full_nda.term == "2_years"
        assert len(full_nda.party) == 2

    def test_party_items_are_party_instances(self, full_nda: NDA) -> None:
        for p in full_nda.party:
            assert isinstance(p, Party)


# ---------------------------------------------------------------------------
# NDA model — serialization
# ---------------------------------------------------------------------------


class TestNDASerialisation:
    def test_model_dump_has_all_keys(self, full_nda: NDA) -> None:
        data = full_nda.model_dump()
        assert set(data.keys()) == {"effective_date", "jurisdiction", "party", "term"}

    def test_model_dump_parties_are_dicts(self, full_nda: NDA) -> None:
        """After model_dump() the nested Party objects become plain dicts."""
        data = full_nda.model_dump()
        for item in data["party"]:
            assert isinstance(item, dict)
            assert "name" in item

    def test_empty_nda_dump(self, empty_nda: NDA) -> None:
        data = empty_nda.model_dump()
        assert data == {
            "effective_date": None,
            "jurisdiction": None,
            "party": [],
            "term": None,
        }
