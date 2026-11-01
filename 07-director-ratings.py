"""Compare IMDb ratings for Tyler Perry and Christopher Nolan.

Films with more than one director are counted once for each name. The rating
used for a director and a film is the mean of those rows.

Steps:
1. Read datasets/movies-clean.csv.
2. Expand the director column and average the rating for each director and film.
3. Compare Tyler Perry and Christopher Nolan with a two-sample t-test.
4. Save the rating density chart.

Inputs:
- datasets/movies-clean.csv from 02-prepare.py.
- Run this from the project folder.

Outputs:
- figures/director-ratings.pdf.
- Means, standard deviations, and the t-test printed to the terminal.

Side effects:
- Creates figures/ if it is not there. Overwrites the PDF.

On failure:
- Exit 1 when the cleaned table is missing, either director has no films, or the chart cannot be saved.

Usage:
    python 07-director-ratings.py
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
FIGURE_PATH = Path("figures/director-ratings.pdf")
DIRECTORS = ("Tyler Perry", "Christopher Nolan")


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


def expand_directors(movies: pd.DataFrame) -> pd.DataFrame:
    """One row per director credit on a film."""
    rows: list[dict[str, object]] = []
    for record in movies.itertuples(index=False):
        for name in str(record.Director).split(","):
            cleaned = name.strip()
            if not cleaned:
                continue
            rows.append(
                {
                    "Movie_Name": record.Movie_Name,
                    "Director": cleaned,
                    "Rating_Score": float(record.Rating_Score),
                }
            )
    if not rows:
        fail(f"{CLEAN_PATH} has no director names. No chart was written.")
    return pd.DataFrame(rows)


def main() -> None:
    """Compare the two directors and save the density chart."""
    # Step 1
    movies = load_movies(CLEAN_PATH)
    for column in ("Movie_Name", "Director", "Rating_Score"):
        if column not in movies.columns:
            fail(f"{CLEAN_PATH} is missing {column}. No chart was written.")

    # Step 2
    credits = expand_directors(movies)
    ratings = (
        credits.groupby(["Director", "Movie_Name"], as_index=False)["Rating_Score"]
        .mean()
    )
    chosen = ratings.loc[ratings["Director"].isin(DIRECTORS)].copy()
    for name in DIRECTORS:
        count = int((chosen["Director"] == name).sum())
        if count == 0:
            fail(f"{name} has no films in {CLEAN_PATH}. No chart was written.")

    # Step 3
    for name in DIRECTORS:
        scores = chosen.loc[chosen["Director"] == name, "Rating_Score"]
        print(f"{name} mean: {scores.mean():.4f}")
        print(f"{name} sd: {scores.std():.4f}")
    perry = chosen.loc[chosen["Director"] == "Tyler Perry", "Rating_Score"]
    nolan = chosen.loc[chosen["Director"] == "Christopher Nolan", "Rating_Score"]
    test = stats.ttest_ind(perry, nolan)
    print(f"t = {test.statistic:.4f} p = {test.pvalue}")

    # Step 4
    FIGURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    grid = sns.displot(
        data=chosen,
        x="Rating_Score",
        hue="Director",
        kind="kde",
        common_norm=False,
    )
    try:
        grid.figure.savefig(FIGURE_PATH, format="pdf", bbox_inches="tight")
    except OSError as error:
        fail(f"Could not write {FIGURE_PATH}: {error}.")
    finally:
        plt.close(grid.figure)
    print(f"Wrote {FIGURE_PATH}.")


if __name__ == "__main__":
    main()
