"""Show each genre's share of mean inflation-adjusted US gross.

A film with several genres is counted in each of them. The pie uses the mean
gross of those rows, which is the comparison the original check plotted.

Steps:
1. Read the cleaned movies and datasets/inflation.csv.
2. Expand genres and adjust US gross to 2023 dollars.
3. Average gross, votes, metascore, and rating by genre.
4. Save the pie chart.

Inputs:
- datasets/movies-clean.csv from 02-prepare.py.
- datasets/inflation.csv.
- Run this from the project folder.

Outputs:
- figures/genre-share.pdf.
- Genres printed from largest mean gross to smallest.

Side effects:
- Creates figures/ if it is not there. Overwrites the PDF.

On failure:
- Exit 1 when an input is missing, a year has no inflation amount, or the chart cannot be saved.

Usage:
    python 06-genre-share.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

CLEAN_PATH = Path("datasets/movies-clean.csv")
INFLATION_PATH = Path("datasets/inflation.csv")
FIGURE_PATH = Path("figures/genre-share.pdf")
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
                    "Meta_Score": float(record.Meta_Score),
                    "Total_Votes": float(record.Total_Votes),
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
    """Average inflation-adjusted gross by genre and save the pie chart."""
    # Step 1
    movies = load_movies(CLEAN_PATH)
    for column in ("Relese_Year", "Rating_Score", "Meta_Score", "Total_Votes", "Gross_USA", "Movie_Genre"):
        if column not in movies.columns:
            fail(f"{CLEAN_PATH} is missing {column}. No chart was written.")
    inflation = load_inflation(INFLATION_PATH)

    # Step 2
    genres = expand_genres(movies)
    genres = adjust_gross(genres, inflation)

    # Step 3
    summary = (
        genres.groupby("Movie_Genre", as_index=False)
        .agg(
            Gross_USA=("Gross_USA", "mean"),
            Total_Votes=("Total_Votes", "mean"),
            Meta_Score=("Meta_Score", "mean"),
            Rating_Score=("Rating_Score", "mean"),
        )
        .sort_values("Gross_USA", ascending=False)
    )
    for _, row in summary.iterrows():
        print(f"{row['Movie_Genre']}: {row['Gross_USA']:.0f}")

    # Step 4
    FIGURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, 7))
    plt.pie(summary["Gross_USA"], autopct="%.0f%%", shadow=False)
    plt.title("Proportion of Movies by Genre")
    plt.legend(labels=summary["Movie_Genre"].tolist())
    try:
        plt.savefig(FIGURE_PATH, format="pdf", bbox_inches="tight")
    except OSError as error:
        fail(f"Could not write {FIGURE_PATH}: {error}.")
    finally:
        plt.close()
    print(f"Wrote {FIGURE_PATH}.")


if __name__ == "__main__":
    main()
