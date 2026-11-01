"""Merge the 2014–2021 IMDb extracts and write the cleaned analysis table.

Steps:
1. Read datasets/movies-2014.csv through datasets/movies-2021.csv.
2. Clean years, names, and numeric columns.
3. Write datasets/movies-clean.csv.

Inputs:
- The eight year CSVs in datasets/.
- Run this from the project folder.

Outputs:
- datasets/movies-clean.csv, the table the analysis scripts read.

Side effects:
- Overwrites datasets/movies-clean.csv when the run succeeds.

On failure:
- Exit 1 when a year file is missing, a column is missing, or a value cannot be cleaned.
  Nothing is written.
- Exit 2 is unused. This script takes no arguments.

Usage:
    python 02-prepare.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

DATA_DIR = Path("datasets")
FIRST_YEAR = 2014
LAST_YEAR = 2021
YEAR_FILES = [DATA_DIR / f"movies-{year}.csv" for year in range(FIRST_YEAR, LAST_YEAR + 1)]
CLEAN_PATH = DATA_DIR / "movies-clean.csv"
SOURCE_COLUMNS = [
    "Movie_Name",
    "Relese_Year",
    "Rating_Score",
    "Meta_Score",
    "Total_Votes",
    "Gross_USA",
    "Movie_Genre",
    "Director_Star",
]
YEAR_PATTERN = re.compile(r"\b\d{4}\b")


def fail(message: str, code: int = 1) -> None:
    """Print one error and stop."""
    print(message, file=sys.stderr)
    raise SystemExit(code)


def read_year(path: Path) -> pd.DataFrame:
    """Read one year extract and keep the source columns."""
    if not path.is_file():
        fail(f"{path} is missing. Nothing was written.")
    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.ParserError, UnicodeError) as error:
        fail(f"Could not read {path}: {error}. Nothing was written.")
    missing = [column for column in SOURCE_COLUMNS if column not in frame.columns]
    if missing:
        fail(f"{path} is missing columns {missing}. Nothing was written.")
    return frame.loc[:, SOURCE_COLUMNS].copy()


def extract_year(value: object) -> int | None:
    """Keep the four-digit year. A trailing slice would turn 2014 into 201."""
    match = YEAR_PATTERN.search(str(value))
    if match is None:
        return None
    return int(match.group())


def split_credits(frame: pd.DataFrame) -> pd.DataFrame:
    """Split 'Director: Name | Stars: Name' into two columns.

    Directors: is removed before Director:. The shorter token is a prefix of the
    longer one, so the other order leaves a stray 's:' on shared credits.
    """
    parts = frame["Director_Star"].astype(str).str.split("|", n=1, expand=True)
    frame = frame.drop(columns=["Director_Star"])
    frame["Director"] = parts[0].str.replace("Directors:", "", regex=False)
    frame["Director"] = frame["Director"].str.replace("Director:", "", regex=False)
    frame["Director"] = frame["Director"].str.replace("Stars:", "", regex=False).str.strip()
    if parts.shape[1] > 1:
        frame["Stars"] = parts[1].str.replace("Stars:", "", regex=False).str.strip()
    else:
        frame["Stars"] = pd.NA
    return frame


def clean(frame: pd.DataFrame) -> pd.DataFrame:
    """Drop empty rows and coerce the columns the analyses use."""
    frame = frame.copy()
    frame["Relese_Year"] = frame["Relese_Year"].map(extract_year)
    frame = frame.dropna()
    frame = frame.loc[frame["Relese_Year"] != 0].copy()
    frame = split_credits(frame)
    for column in ("Gross_USA", "Meta_Score", "Total_Votes"):
        coerced = pd.to_numeric(frame[column], errors="coerce")
        if coerced.isna().any():
            fail(f"{column} has values that are not numbers. {CLEAN_PATH} was not written.")
        frame[column] = coerced.astype("int64")
    frame["Rating_Score"] = pd.to_numeric(frame["Rating_Score"], errors="coerce")
    frame["Relese_Year"] = frame["Relese_Year"].astype("int64")
    frame = frame.dropna(subset=["Rating_Score", "Movie_Name", "Movie_Genre", "Director"])
    return frame.reset_index(drop=True)


def write_table(frame: pd.DataFrame, path: Path, previous: str) -> None:
    """Write one CSV. previous names the file already saved, if this write fails."""
    try:
        frame.to_csv(path, index=False)
    except OSError as error:
        extra = f" {previous}" if previous else " Nothing else was written."
        fail(f"Could not write {path}: {error}.{extra}")


def main() -> None:
    """Merge the year files, then write the cleaned table."""
    # Step 1
    frames = [read_year(path) for path in YEAR_FILES]

    # Step 2
    merged = pd.concat(frames, ignore_index=True)
    cleaned = clean(merged)
    if cleaned.empty:
        fail(f"Cleaning removed every row. {CLEAN_PATH} was not written.")

    # Step 3
    write_table(cleaned, CLEAN_PATH, "")
    print(f"Wrote {len(cleaned)} rows to {CLEAN_PATH}.")


if __name__ == "__main__":
    main()
