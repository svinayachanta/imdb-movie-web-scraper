"""Plot total US gross by release year for 2014–2021.

Steps:
1. Read datasets/movies-clean.csv.
2. Sum US gross for each release year.
3. Save the line chart.

Inputs:
- datasets/movies-clean.csv from 02-prepare.py.
- Run this from the project folder.

Outputs:
- figures/gross-by-year.pdf.
- The year totals printed to the terminal.

Side effects:
- Creates figures/ if it is not there. Overwrites the PDF.

On failure:
- Exit 1 when the cleaned table is missing or the chart cannot be saved.
  No PDF is written when the table cannot be read.

Usage:
    python 03-gross-by-year.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

CLEAN_PATH = Path("datasets/movies-clean.csv")
FIGURE_PATH = Path("figures/gross-by-year.pdf")


def fail(message: str, code: int = 1) -> None:
    """Print one error and stop."""
    print(message, file=sys.stderr)
    raise SystemExit(code)


def load_movies(path: Path) -> pd.DataFrame:
    """Read the cleaned table, or stop with the command that creates it."""
    if not path.is_file():
        fail(f"{path} is missing. Run 02-prepare.py from this folder. No chart was written.")
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError, UnicodeError) as error:
        fail(f"Could not read {path}: {error}. No chart was written.")


def main() -> None:
    """Sum gross by year and save the line chart."""
    # Step 1
    movies = load_movies(CLEAN_PATH)
    for column in ("Relese_Year", "Gross_USA"):
        if column not in movies.columns:
            fail(f"{CLEAN_PATH} is missing {column}. No chart was written.")

    # Step 2
    totals = (
        movies.groupby("Relese_Year", as_index=False)["Gross_USA"]
        .sum()
        .sort_values("Relese_Year")
    )
    for _, row in totals.iterrows():
        print(f"{int(row['Relese_Year'])}: {int(row['Gross_USA'])}")

    # Step 3
    FIGURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(6, 4))
    axis = sns.lineplot(data=totals, x="Relese_Year", y="Gross_USA")
    axis.tick_params(labelsize=8)
    plt.title("Gross Revenue of Movies Trended from 2014 to 2021", fontsize=15)
    plt.xlabel("Year", fontsize=9)
    plt.ylabel("Total Gross Revenue", fontsize=9)
    try:
        plt.savefig(FIGURE_PATH, format="pdf", bbox_inches="tight")
    except OSError as error:
        fail(f"Could not write {FIGURE_PATH}: {error}.")
    finally:
        plt.close()
    print(f"Wrote {FIGURE_PATH}.")


if __name__ == "__main__":
    main()
