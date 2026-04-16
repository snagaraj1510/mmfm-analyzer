"""CSV and TSV file handler."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def parse_csv(file_path: Path | str, delimiter: str = ",") -> pd.DataFrame:
    """
    Parse a CSV or TSV file into a DataFrame.

    Args:
        file_path: Path to the CSV/TSV file
        delimiter: Column separator (default comma; use '\t' for TSV)

    Returns:
        DataFrame with stripped column names
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Auto-detect TSV
    if path.suffix.lower() == ".tsv":
        delimiter = "\t"

    df = pd.read_csv(path, sep=delimiter, dtype=str)
    df.columns = [str(col).strip() for col in df.columns]
    df = df.dropna(how="all")
    return df
