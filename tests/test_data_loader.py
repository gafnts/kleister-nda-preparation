"""
Tests for data_loader.py
(DataLoader: compressed TSV input + labels by partition)
"""

import lzma
from pathlib import Path

import pytest

from nda.data_loader import DataLoader


def _write_xz(path: Path, content: str) -> None:
    """Write a string as an xz-compressed file."""
    with lzma.open(path, "wt", encoding="utf-8") as f:
        f.write(content)


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """Create a minimal dataset directory with header, partitions, and labels."""
    (tmp_path / "in-header.tsv").write_text("col_a\tcol_b\n", encoding="utf-8")

    for name, rows, labels in [
        ("train", "alice\t1\nbob\t2\n", "pos\nneg\n"),
        ("dev-0", "carol\t3\n", "pos\n"),
    ]:
        part = tmp_path / name
        part.mkdir()
        _write_xz(part / "in.tsv.xz", rows)
        (part / "expected.tsv").write_text(labels, encoding="utf-8")

    test_a = tmp_path / "test-A"
    test_a.mkdir()
    _write_xz(test_a / "in.tsv.xz", "dave\t4\n")

    return tmp_path


@pytest.fixture
def loader(data_dir: Path) -> DataLoader:
    """Return a DataLoader pointed at the fixture directory."""
    return DataLoader(data_dir)


class TestColumnDiscovery:
    def test_columns_read_from_header_file(self, loader: DataLoader) -> None:
        assert loader._column_names == ["col_a", "col_b"]

    def test_missing_header_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            DataLoader(tmp_path)


class TestLoadTrain:
    def test_default_partition_is_train(self, loader: DataLoader) -> None:
        df = loader.load()
        assert len(df) == 2

    def test_includes_input_columns(self, loader: DataLoader) -> None:
        df = loader.load("train")
        assert "col_a" in df.columns
        assert "col_b" in df.columns

    def test_includes_labels(self, loader: DataLoader) -> None:
        df = loader.load("train")
        assert "labels" in df.columns

    def test_values_match_fixture_data(self, loader: DataLoader) -> None:
        df = loader.load("train")
        assert df["col_a"].tolist() == ["alice", "bob"]
        assert df["labels"].tolist() == ["pos", "neg"]


class TestLoadDev:
    def test_includes_labels(self, loader: DataLoader) -> None:
        df = loader.load("dev-0")
        assert "labels" in df.columns

    def test_row_count(self, loader: DataLoader) -> None:
        df = loader.load("dev-0")
        assert len(df) == 1


class TestLoadTest:
    def test_excludes_labels(self, loader: DataLoader) -> None:
        df = loader.load("test-A")
        assert "labels" not in df.columns

    def test_includes_input_columns(self, loader: DataLoader) -> None:
        df = loader.load("test-A")
        assert list(df.columns) == ["col_a", "col_b"]

    def test_values_match_fixture_data(self, loader: DataLoader) -> None:
        df = loader.load("test-A")
        assert df["col_a"].tolist() == ["dave"]
