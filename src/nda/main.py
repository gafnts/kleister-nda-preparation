"""
Entry point for the preprocessing pipeline.
Prepares and delivers the Kleister NDA dataset for multimodal KIE tasks, in such a way that:
- Loads raw data for all partitions
- Parses ground truth labels into a validated schema
- Relocates source documents into an output directory, organized by partition
- Persists processed dataframes as parquet files in each output partition directory
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
    Deliver the preprocessed dataset to a specified output directory.
    """
    parser = argparse.ArgumentParser(description="Run the NDA preprocessing pipeline.")
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Directory where processed outputs are written (default: {OUTPUT_DIR}).",
    )
    return parser.parse_args()


def load_data() -> list[pd.DataFrame]:
    """
    Load raw data for all partitions from the data directory.
    """
    logger.info("Loading data for partitions: %s", PARTITIONS)
    loader = DataLoader(DATA_DIR)
    dataframes = [loader.load(partition) for partition in PARTITIONS]
    logger.info("Loaded dataframes: %s", [df.shape for df in dataframes])
    return dataframes


def parse_labels(
    dataframes: list[pd.DataFrame],
) -> list[pd.DataFrame]:
    """
    Apply label transformations to all partition dataframes.
    """
    logger.info("Parsing labels for all partitions")
    transformed = [
        label_transformer.transform(df, partition)
        for df, partition in zip(dataframes, PARTITIONS, strict=True)
    ]
    logger.info("Labels parsed for all partitions")
    return transformed


def relocate_documents(dataframes: list[pd.DataFrame], output_dir: Path) -> None:
    """
    Copy source documents into the output directory, organized by partition.
    """
    logger.info("Relocating documents for all partitions")
    utils.relocate_documents(
        dataframes,
        PARTITIONS,
        DATA_DIR,
        output_dir,
    )
    logger.info("Documents relocated for all partitions")


def store_parquets(dataframes: list[pd.DataFrame], output_dir: Path) -> None:
    """
    Persist all partition dataframes as parquet files in the output directory.
    """
    logger.info("Storing parquets for partitions: %s", PARTITIONS)
    utils.to_parquet(dataframes, PARTITIONS, output_dir)
    logger.info("All partitions have been stored as parquet")


def main() -> None:
    """
    Run the full NDA preprocessing pipeline end-to-end.
    Produces processed parquets and relocated documents
    ordered by partition in the specified output directory.
    """
    logger.info("Starting the NDA preprocessing pipeline")
    args = parse_args()

    logger.info("1. Data loading")
    dataframes = load_data()

    logger.info("2. Label parsing")
    dataframes = parse_labels(dataframes)

    logger.info("3. Document relocation")
    relocate_documents(dataframes, args.output_dir)

    logger.info("4. Parquet file storage")
    store_parquets(dataframes, args.output_dir)

    logger.info("Pipeline completed.")
    logger.info(f"Data is available in: {args.output_dir}")


if __name__ == "__main__":
    main()
