"""
Tests for data_loader.py  (DataLoader class)

New concepts introduced here:
  - tmp_path  — pytest's built-in fixture that gives you a fresh temporary
                directory for each test; it's automatically cleaned up afterwards
  - conftest.py-style shared fixtures — here we define them in the same file,
    but they can be moved to tests/conftest.py so multiple test files can share them
"""

from pathlib import Path

import pandas as pd
import pytest

from nda.data_loader import DataLoader

# ---------------------------------------------------------------------------
# Helpers — build the fake on-disk directory structure
# ---------------------------------------------------------------------------

COLUMNS = [
    "filename",
    "keys",
    "text_djvu",
    "text_tesseract",
    "text_textract",
    "text_best",
]

SAMPLE_ROWS = [
    ["doc_a.pdf", "key1", "djvu text a", "tess text a", "textract a", "best a"],
    ["doc_b.pdf", "key2", "djvu text b", "tess text b", "textract b", "best b"],
]

SAMPLE_LABELS = [
    "effective_date=2020-01-01 party=Acme",
    "jurisdiction=Delaware term=2_years",
]


def _write_data_dir(tmp_path: Path, partition: str) -> Path:
    """
    Build the minimal directory structure that DataLoader expects:

        <tmp_path>/
            in-header.tsv          ← column names, no data rows
            <partition>/
                in.tsv.xz          ← compressed data
                expected.tsv       ← labels (only for train / dev-0)
    """
    # Header file (a TSV with just the column names, zero data rows)
    header_df = pd.DataFrame(columns=COLUMNS)
    header_df.to_csv(tmp_path / "in-header.tsv", sep="\t", index=False)

    # Partition directory
    partition_dir = tmp_path / partition
    partition_dir.mkdir()

    # Compressed input data (xz) — pandas writes it automatically when the
    # file extension ends in .xz
    data_df = pd.DataFrame(SAMPLE_ROWS, columns=COLUMNS)
    data_df.to_csv(
        partition_dir / "in.tsv.xz",
        sep="\t",
        index=False,
        header=False,
        compression="xz",
    )

    # Labels (plain TSV, no header)
    if partition != "test-A":
        labels_df = pd.DataFrame(SAMPLE_LABELS, columns=["labels"])
        labels_df.to_csv(
            partition_dir / "expected.tsv",
            sep="\t",
            index=False,
            header=False,
        )

    return tmp_path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
# tmp_path is a built-in pytest fixture: just add it as a parameter and
# pytest hands you a fresh pathlib.Path for a temporary directory.


@pytest.fixture
def train_data_dir(tmp_path):
    """A data_dir with a valid 'train' partition."""
    return _write_data_dir(tmp_path, "train")


@pytest.fixture
def test_a_data_dir(tmp_path):
    """A data_dir with a valid 'test-A' partition (no labels file)."""
    return _write_data_dir(tmp_path, "test-A")


# ---------------------------------------------------------------------------
# DataLoader — construction
# ---------------------------------------------------------------------------


class TestDataLoaderInit:
    def test_reads_column_names_from_header(self, train_data_dir):
        """DataLoader should parse column names from in-header.tsv on init."""
        loader = DataLoader(train_data_dir)
        assert loader._column_names == COLUMNS

    def test_raises_if_header_missing(self, tmp_path):
        """If in-header.tsv is absent, DataLoader __init__ should raise FileNotFoundError."""
        # tmp_path is empty — no header file written
        with pytest.raises(FileNotFoundError):
            DataLoader(tmp_path)


# ---------------------------------------------------------------------------
# DataLoader.load
# ---------------------------------------------------------------------------


class TestDataLoaderLoad:
    def test_load_train_returns_dataframe(self, train_data_dir):
        loader = DataLoader(train_data_dir)
        df = loader.load("train")
        assert isinstance(df, pd.DataFrame)

    def test_load_train_has_expected_columns(self, train_data_dir):
        """train partition must have all input columns PLUS a 'labels' column."""
        loader = DataLoader(train_data_dir)
        df = loader.load("train")
        assert set(COLUMNS).issubset(df.columns)
        assert "labels" in df.columns

    def test_load_train_row_count_matches_input(self, train_data_dir):
        loader = DataLoader(train_data_dir)
        df = loader.load("train")
        assert len(df) == len(SAMPLE_ROWS)

    def test_load_train_labels_match_expected_file(self, train_data_dir):
        loader = DataLoader(train_data_dir)
        df = loader.load("train")
        assert df["labels"].tolist() == SAMPLE_LABELS

    def test_load_test_a_has_no_labels_column(self, test_a_data_dir):
        """test-A has no expected.tsv, so the returned DataFrame should NOT have 'labels'."""
        loader = DataLoader(test_a_data_dir)
        df = loader.load("test-A")
        assert "labels" not in df.columns

    def test_load_test_a_still_has_input_columns(self, test_a_data_dir):
        loader = DataLoader(test_a_data_dir)
        df = loader.load("test-A")
        assert set(COLUMNS).issubset(df.columns)
