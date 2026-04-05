# Kleister NDA: Dataset Preparation for LLM-based KIE

[![CI](https://github.com/gafnts/kleister-nda-preparation/actions/workflows/ci.yaml/badge.svg)](https://github.com/gafnts/kleister-nda-preparation/actions/workflows/ci.yaml)
[![codecov](https://codecov.io/github/gafnts/kleister-nda-preparation/graph/badge.svg?token=JNN2IC5C2B)](https://codecov.io/github/gafnts/kleister-nda-preparation)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A Python package for preparing and delivering the [Kleister NDA](https://github.com/applicaai/kleister-nda) dataset for multimodal Key Information Extraction (KIE) tasks using large language models in a serverless processing context.

The pipeline reads the original dataset partitions, transforms raw TSV labels into structured records validated against a Pydantic schema, relocates the corresponding PDF documents, and writes the results as partitioned Parquet files ready for downstream inference workflows.

## Contents

- [Installation](#installation)
- [Running the preparation and delivery pipeline](#running-the-preparation-and-delivery-pipeline)
- [Output structure](#output-structure)
- [NDA schema](#nda-schema)
- [Original dataset documentation](#original-dataset-documentation)
  - [Evaluation](#evaluation)
  - [Directory structure](#directory-structure)
  - [Structure of data sets](#structure-of-data-sets)
  - [Format of the test sets](#format-of-the-test-sets)
  - [Information to be extracted](#information-to-be-extracted)
  - [Normalization](#normalization)
  - [Format of the output files for test sets](#format-of-the-output-files-for-test-sets)
- [Contributing](#contributing)
- [Sources](#sources)

---

## Installation

The package requires Python 3.13 or later. Dependencies are managed with [uv](https://docs.astral.sh/uv/).

To use this package in your own project, add it as a dependency directly from GitHub:

```bash
uv add git+https://github.com/gafnts/kleister-nda-preparation
```

---

## Running the preparation and delivery pipeline

The package exposes a single CLI entry point that executes the full pipeline. By default, outputs are delivered to a `data/` folder in the current working directory:

```bash
uv run nda
```

Pass `--output_dir` to override the destination:

```bash
uv run nda --output_dir /path/to/output
```

The pipeline performs the following steps in sequence:

1. **Load**: Reads the compressed TSV input files and, where available, the corresponding `expected.tsv` label files for each partition (`train`, `dev-0`, `test-A`).
2. **Transform**: Parses the raw label strings into structured dictionaries validated against the `NDA` Pydantic model, which is the official schema of the extraction task.
3. **Relocate**: Copies each partition's PDF documents from the shared `documents/` directory into the corresponding partition output directory.
4. **Store**: Serialises each partition's DataFrame as a gzip-compressed Parquet file.

Since this package serves a one-time preparation purpose, you can remove it from your project after the pipeline has run:

```bash
uv remove nda
```

---

## Output structure

Running the pipeline creates an `outputs/` directory under the specified path, organised by partition:

```
src/nda/static/outputs/
├── train/
│   ├── data.parquet
│   └── documents/
│       ├── <md5>.pdf
│       └── ...
├── dev-0/
│   ├── data.parquet
│   └── documents/
│       ├── <md5>.pdf
│       └── ...
└── test-A/
    ├── data.parquet
    └── documents/
        ├── <md5>.pdf
        └── ...
```

Each `data.parquet` file contains one row per document. For the `train` and `dev-0` partitions, the dataset includes the raw input columns alongside the following label columns:

| Column | Description |
|---|---|
| `labels` | Raw label string from `expected.tsv` |
| `labels_canonical` | Label string sorted to match the schema field order |
| `labels_schema` | Structured dictionary produced by `NDA.model_dump()` |
| `labels_serialized` | Normalised label string reconstructed from the schema |

The `test-A` partition contains only input columns, as ground truth labels are withheld.

The `documents/` subdirectory within each partition contains only the PDF files referenced by that partition's records.

---

## NDA schema

Labels are validated and serialised through the `NDA` Pydantic model, which is the canonical schema for the extraction task:

```python
class NDA(BaseModel):
    effective_date: str | None  # YYYY-MM-DD
    jurisdiction: str | None    # state or country
    party: list[Party]          # one or more contracting parties
    term: str | None            # e.g. "12_months"
```

All spaces and colons in field values are replaced with underscores. Dates are expressed in `YYYY-MM-DD` format. Contract terms are normalised to `{number}_{units}` form (e.g. `eleven months` becomes `11_months`).

---

## Original dataset documentation

The sections below are reproduced from the [Kleister NDA dataset documentation](https://github.com/applicaai/kleister-nda) for reference. The original directory structure is preserved verbatim under `src/nda/static/data/`.

### Evaluation

Evaluation is carried out using [GEval](https://gitlab.com/filipg/geval) against `out.tsv` files in the same format as `expected.tsv`:

```
wget https://gonito.net/get/bin/geval
chmod u+x geval
./geval -t dev-0
```

The primary metric is F1 score calculated on upper-cased values. F1 on true-cased values is reported as an auxiliary metric.

### Directory structure

```
src/nda/static/data/
├── README.md
├── config.txt              — GEval configuration file
├── in-header.tsv           — column names for input data
├── train/
│   ├── in.tsv.xz           — input data
│   └── expected.tsv        — reference labels
├── dev-0/
│   ├── in.tsv.xz
│   └── expected.tsv
├── test-A/
│   ├── in.tsv.xz
│   └── expected.tsv        — hidden
└── documents/              — all PDFs, referenced in TSV files
```

Files are sorted by MD5 hash. TSV files use tab as the sole delimiter; double quotes are not treated as special characters (`QUOTE_NONE` in Python's `csv` module).

### Structure of data sets

The dataset was split in a stable pseudorandom manner using MD5 fingerprints of document contents:

| Partition | Items |
|---|---|
| train | 254 |
| dev-0 | 83 |
| test-A | 203 |

### Format of the test sets

Each `in.tsv.xz` file contains six tab-separated columns per row:

1. Document filename (MD5 hash with file extension), referencing a file in `documents/`
2. Alphabetically ordered list of keys to be predicted, space-separated
3. Plain text from pdf2djvu/djvu2hocr
4. Plain text from Tesseract
5. Plain text from Textract
6. Combined text from pdf2djvu/djvu2hocr and Tesseract

End-of-line characters, tabs, and non-printable characters in the text columns are replaced with spaces to avoid conflicts with TSV formatting.

The following escape sequences appear in the OCR-extracted text:

| Sequence | Meaning |
|---|---|
| `\f` | Page break |
| `\n` | End of line |
| `\t` | Tabulation |
| `\\` | Literal backslash |

### Information to be extracted

Up to four attributes are extracted from each document:

| Attribute | Description |
|---|---|
| `effective_date` | Date (`YYYY-MM-DD`) at which the contract becomes legally binding |
| `jurisdiction` | State or country jurisdiction under which the contract is signed |
| `party` | Contracting party or parties (may appear multiple times) |
| `term` | Length of the contract as expressed in the document |

Not every document contains all four attributes. Keys with no corresponding value are omitted from `expected.tsv`; they are not given with an empty value.

### Normalization

| Rule | Detail |
|---|---|
| Spaces and colons in values | Replaced with underscores |
| Dates | Returned in `YYYY-MM-DD` format |
| Contract term | Normalised to `{number}_{units}` (e.g. `eleven months` → `11_months`) |

### Format of the output files for test sets

The output format matches `expected.tsv`: a list of `key=value` pairs, one document per line, sorted alphabetically by key. The order of pairs within a line does not matter. Multiple values for the same key (e.g. multiple parties) appear as separate `key=value` tokens on the same line.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, available Make targets, and CI details.

---

## Sources

- Dataset repository: [https://github.com/applicaai/kleister-nda](https://github.com/applicaai/kleister-nda)
- Dataset paper: Gralinski et al., "Kleister: A novel long-document dataset for information extraction", arXiv:2105.05796 — [https://arxiv.org/abs/2105.05796](https://arxiv.org/abs/2105.05796)
- Original data source: [Edgar Database](https://www.sec.gov/edgar.shtml)
