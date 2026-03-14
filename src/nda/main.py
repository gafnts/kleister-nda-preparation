"""
Prepares and delivers the Kleister NDA dataset for multimodal KIE tasks by:
    - Loading raw data for all partitions
    - Parsing ground truth labels into a validated schema
    - Relocating source documents into an output directory, organized by partition
    - Persisting prepared dataframes as parquet files in each output partition directory
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

from nda import label_transformer, utils
from nda.data_loader import DataLoader, Partition

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


DATA_DIR: Path = Path(__file__).parent / "static" / "data"
OUTPUT_DIR: Path = Path(__file__).parent / "static" / "outputs"
PARTITIONS: tuple[Partition, ...] = ("train", "dev-0", "test-A")


def parse_args() -> argparse.Namespace:
    """
    Deliver the prepared dataset to a specified output directory.
    """
    parser = argparse.ArgumentParser(
        description="Run the Kleister NDA preparation pipeline."
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Directory where prepared outputs are delivered (default: {OUTPUT_DIR}).",
    )
    return parser.parse_args()


def load_data() -> list[pd.DataFrame]:
    """
    Load raw data for all partitions from the data directory.
    """
    loader = DataLoader(DATA_DIR)
    dataframes = [loader.load(partition) for partition in PARTITIONS]
    return dataframes


def parse_labels(
    dataframes: list[pd.DataFrame],
) -> list[pd.DataFrame]:
    """
    Apply label transformations to all partition dataframes.
    """
    transformed = [
        label_transformer.transform(df, partition)
        for df, partition in zip(dataframes, PARTITIONS, strict=True)
    ]
    return transformed


def relocate_documents(dataframes: list[pd.DataFrame], output_dir: Path) -> None:
    """
    Copy source documents into the output directory, organized by partition.
    """
    utils.relocate_documents(
        dataframes,
        PARTITIONS,
        DATA_DIR,
        output_dir,
    )


def store_parquets(dataframes: list[pd.DataFrame], output_dir: Path) -> None:
    """
    Persist all partition dataframes as parquet files in the output directory.
    """
    utils.to_parquet(dataframes, PARTITIONS, output_dir)


def main() -> None:
    """
    Run the preparation pipeline end-to-end.
    """
    logger.info("Starting the Kleister NDA dataset preparation")
    args = parse_args()

    logger.info("1. Loading TSV data into dataframes")
    dataframes = load_data()

    logger.info("2. Parsing and validating labels")
    dataframes = parse_labels(dataframes)

    logger.info("3. Relocating source documents to output directory")
    relocate_documents(dataframes, args.output_dir)

    logger.info("4. Persisting dataframes as parquet files")
    store_parquets(dataframes, args.output_dir)

    logger.info("The preparation has completed")
    logger.info(f"Data is available in: {args.output_dir}")


if __name__ == "__main__":
    main()
