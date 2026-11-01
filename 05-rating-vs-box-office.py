"""Test whether IMDb rating and inflation-adjusted gross move together.

A film with several genres is repeated once per genre, which is how the original
check weighted multi-genre titles. Gross is then scaled into 2023 dollars.

Steps:
1. Read the cleaned movies and datasets/inflation.csv.
2. Expand genres and adjust US gross to 2023 dollars.
3. Average that gross at each rating and fit a Pearson correlation.
4. Save the scatter plot.

Inputs:
- datasets/movies-clean.csv from 02-prepare.py.
- datasets/inflation.csv, with year, amount, and inflation rate.
- Run this from the project folder.

Outputs:
- figures/rating-vs-box-office.pdf.
- The Pearson r and p-value printed to the terminal.

Side effects:
- Creates figures/ if it is not there. Overwrites the PDF.

On failure:
- Exit 1 when an input is missing, a year has no inflation amount, or the chart cannot be saved.

Usage:
    python 05-rating-vs-box-office.py
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
INFLATION_PATH = Path("datasets/inflation.csv")
FIGURE_PATH = Path("figures/rating-vs-box-office.pdf")
REFERENCE_YEAR = 2023


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


def load_inflation(path: Path) -> pd.DataFrame:
    """Read the price index and keep year plus amount."""
    if not path.is_file():
        fail(f"{path} is missing. No chart was written.")
    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.ParserError, UnicodeError) as error:
        fail(f"Could not read {path}: {error}. No chart was written.")
    if frame.shape[1] < 2:
        fail(f"{path} needs a year column and an amount column. No chart was written.")
    frame = frame.iloc[:, :2].copy()
    frame.columns = ["Relese_Year", "amount"]
    frame["Relese_Year"] = pd.to_numeric(frame["Relese_Year"], errors="coerce")
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    frame = frame.dropna()
    frame["Relese_Year"] = frame["Relese_Year"].astype(int)
    return frame


def expand_genres(movies: pd.DataFrame) -> pd.DataFrame:
    """Repeat each film once for every genre name in its list."""
    rows: list[dict[str, object]] = []
    for record in movies.itertuples(index=False):
        for genre in str(record.Movie_Genre).split(","):
            name = genre.strip()
            if not name:
                continue
            rows.append(
                {
                    "Relese_Year": int(record.Relese_Year),
                    "Rating_Score": float(record.Rating_Score),
                    "Gross_USA": float(record.Gross_USA),
                    "Movie_Genre": name,
                }
            )
    if not rows:
        fail(f"{CLEAN_PATH} has no genres to expand. No chart was written.")
    return pd.DataFrame(rows)


def adjust_gross(genres: pd.DataFrame, inflation: pd.DataFrame) -> pd.DataFrame:
    """Scale US gross into REFERENCE_YEAR dollars using the index amount."""
    reference = inflation.loc[inflation["Relese_Year"] == REFERENCE_YEAR, "amount"]
    if reference.empty:
        fail(f"{INFLATION_PATH} has no {REFERENCE_YEAR} amount. Gross was not adjusted. No chart was written.")
    factor = float(reference.iloc[0])
    merged = genres.merge(inflation, on="Relese_Year", how="left")
    missing = int(merged["amount"].isna().sum())
    if missing:
        fail(
            f"{missing} rows have a release year that is not in {INFLATION_PATH}. "
            "Gross was not adjusted. No chart was written."
        )
    adjusted = genres.copy()
    adjusted["Gross_USA"] = adjusted["Gross_USA"].to_numpy() * factor / merged["amount"].to_numpy()
    return adjusted


def main() -> None:
    """Correlate rating with inflation-adjusted gross and save the plot."""
    # Step 1
    movies = load_movies(CLEAN_PATH)
    for column in ("Relese_Year", "Rating_Score", "Gross_USA", "Movie_Genre"):
        if column not in movies.columns:
            fail(f"{CLEAN_PATH} is missing {column}. No chart was written.")
    inflation = load_inflation(INFLATION_PATH)

    # Step 2
    genres = expand_genres(movies)
    genres = adjust_gross(genres, inflation)

    # Step 3
    by_rating = genres.groupby("Rating_Score", as_index=False)["Gross_USA"].mean()
    if len(by_rating) < 3:
        fail("Not enough distinct ratings to correlate. No chart was written.")
    correlation = stats.pearsonr(by_rating["Rating_Score"], by_rating["Gross_USA"])
    print(f"r = {correlation.statistic:.4f} p = {correlation.pvalue}")

    # Step 4
    FIGURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    sns.regplot(
        data=by_rating,
        x="Rating_Score",
        y="Gross_USA",
        scatter_kws={"s": 3},
        line_kws={"color": "red"},
    )
    plt.title("Correlation Between Ratings and Box Office Revenue", fontsize=12)
    plt.xlabel("Ratings", fontsize=10)
    plt.ylabel("Total Gross Revenue", fontsize=10)
    try:
        plt.savefig(FIGURE_PATH, format="pdf", bbox_inches="tight")
    except OSError as error:
        fail(f"Could not write {FIGURE_PATH}: {error}.")
    finally:
        plt.close()
    print(f"Wrote {FIGURE_PATH}.")


if __name__ == "__main__":
    main()
