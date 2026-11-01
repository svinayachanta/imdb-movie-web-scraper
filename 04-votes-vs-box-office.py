"""Test whether IMDb votes and US gross move together.

Steps:
1. Read datasets/movies-clean.csv.
2. Fit a Pearson correlation of votes against US gross.
3. Save the scatter plot with its regression line.

Inputs:
- datasets/movies-clean.csv from 02-prepare.py.
- Run this from the project folder.

Outputs:
- figures/votes-vs-box-office.pdf.
- The Pearson r and p-value printed to the terminal.

Side effects:
- Creates figures/ if it is not there. Overwrites the PDF.

On failure:
- Exit 1 when the cleaned table is missing, a column is missing, or the chart cannot be saved.

Usage:
    python 04-votes-vs-box-office.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scipy import stats

CLEAN_PATH = Path("datasets/movies-clean.csv")
FIGURE_PATH = Path("figures/votes-vs-box-office.pdf")


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
    """Correlate votes with US gross and save the plot."""
    # Step 1
    movies = load_movies(CLEAN_PATH)
    for column in ("Total_Votes", "Gross_USA"):
        if column not in movies.columns:
            fail(f"{CLEAN_PATH} is missing {column}. No chart was written.")
    pair = movies.loc[:, ["Total_Votes", "Gross_USA"]].dropna()
    if len(pair) < 3:
        fail(f"{CLEAN_PATH} does not have enough rows to correlate. No chart was written.")

    # Step 2
    correlation = stats.pearsonr(pair["Total_Votes"], pair["Gross_USA"])
    print(f"r = {correlation.statistic:.4f} p = {correlation.pvalue}")

    # Step 3
    FIGURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(5, 5))
    axis = sns.regplot(
        data=pair,
        x="Total_Votes",
        y="Gross_USA",
        color="blue",
        line_kws={"color": "red"},
        scatter_kws={"color": "blue"},
    )
    axis.tick_params(labelsize=8)
    plt.title("Correlation Between IMDb Votes and Box Office Revenue", fontsize=12)
    plt.xlabel("Number of Votes on IMDb", fontsize=10)
    plt.ylabel("Total Gross Revenue of Movies", fontsize=10)
    try:
        plt.savefig(FIGURE_PATH, format="pdf", bbox_inches="tight")
    except OSError as error:
        fail(f"Could not write {FIGURE_PATH}: {error}.")
    finally:
        plt.close()
    print(f"Wrote {FIGURE_PATH}.")


if __name__ == "__main__":
    main()
