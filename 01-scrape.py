"""Scrape one year of IMDb feature films into a CSV.

The year files already in datasets/ were collected this way. Re-run this only
when you want a fresh extract. The later scripts do not call IMDb.

Steps:
1. Read the year, row count, and output path.
2. Page through the IMDb title search until that many films are collected.
3. Write the CSV.

Inputs:
- --year, default 2016. Release year in the search URL.
- --count, default 200. How many films to keep.
- --output, default datasets/sample.csv.

Outputs:
- The CSV named by --output, with the same columns as the year files.

Side effects:
- Sends HTTP requests to IMDb. Waits one second between pages.

On failure:
- Exit 2 when the year or count is not usable. Nothing is written.
- Exit 1 when IMDb does not return the old listing markup, or the request fails.
  A short file is still written when some rows were parsed and a later page stopped.
  Nothing is written when zero rows were parsed.

Usage:
    python 01-scrape.py
    python 01-scrape.py --year 2016 --count 200 --output datasets/sample.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import bs4
import requests

DEFAULT_YEAR = 2016
DEFAULT_COUNT = 200
DEFAULT_OUTPUT = Path("datasets/sample.csv")
MIN_YEAR = 1900
MAX_YEAR = 2100
PAGE_PAUSE_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 30
MAX_PAGES = 40
SEARCH_URL = (
    "https://www.imdb.com/search/title/?title_type=feature"
    "&release_date={year}-01-01,{year}-12-31"
    "&sort=boxoffice_gross_us,desc&start={start}"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
COLUMNS = [
    "Movie_Name",
    "Relese_Year",
    "Rating_Score",
    "Meta_Score",
    "Total_Votes",
    "Gross_USA",
    "Movie_Genre",
    "Director_Star",
]


def fail(message: str, code: int) -> None:
    """Print one error and stop. code is 1 for a failed scrape and 2 for bad arguments."""
    print(message, file=sys.stderr)
    raise SystemExit(code)


def parse_args() -> argparse.Namespace:
    """Read the year, row count, and output path."""
    parser = argparse.ArgumentParser(description="Scrape one IMDb release year into a CSV.")
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR, help="Release year to search.")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="How many films to keep.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="CSV path to write. Parent folders are created.",
    )
    args = parser.parse_args()
    if args.year < MIN_YEAR or args.year > MAX_YEAR:
        fail(f"--year must be between {MIN_YEAR} and {MAX_YEAR}. Nothing was written.", 2)
    if args.count < 1:
        fail("--count must be at least 1. Nothing was written.", 2)
    return args


def fetch_page(session: requests.Session, url: str) -> bs4.BeautifulSoup:
    """Download one search page. Raises requests.RequestException on a network failure."""
    response = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return bs4.BeautifulSoup(response.text, "html.parser")


def page_end(soup: bs4.BeautifulSoup) -> int | None:
    """Return the last row number shown on this page, such as 50 in '1-50 of ...'."""
    nav = soup.find("div", {"class": "nav"})
    if nav is None:
        return None
    desc = nav.find("div", {"class": "desc"})
    if desc is None or len(desc.contents) < 2:
        return None
    try:
        text = desc.contents[1].get_text()
        end_token = text.split("-")[1].split(" ")[0].replace(",", "")
        return int(end_token)
    except (AttributeError, IndexError, ValueError):
        return None


def parse_listing(col: bs4.element.Tag) -> dict[str, object]:
    """Pull one film from an old IMDb lister card. Missing fields stay empty."""
    name = col.find("a")
    year = col.find("span", {"class": "lister-item-year"})
    rating = col.find("div", {"class": "inline-block ratings-imdb-rating"})
    metascore = col.find("span", {"class": "metascore"})
    vote_nodes = col.find_all("span", {"name": "nv"})
    votes = vote_nodes[0] if vote_nodes else None
    gross = vote_nodes[-1] if vote_nodes else None
    genre = col.find("span", class_="genre")
    paragraphs = col.find_all("p")
    director = paragraphs[2] if len(paragraphs) > 2 else None

    release_year = None
    if year is not None and year.contents:
        raw_year = str(year.contents[0])
        release_year = raw_year[1:-1].replace("I) (", "").strip()

    return {
        "Movie_Name": name.get_text(strip=True) if name else None,
        "Relese_Year": release_year,
        "Rating_Score": float(rating.get("data-value")) if rating and rating.get("data-value") else None,
        "Meta_Score": float(metascore.get_text(strip=True)) if metascore else None,
        "Total_Votes": int(votes.get("data-value").replace(",", "")) if votes and votes.get("data-value") else None,
        "Gross_USA": int(gross.get("data-value").replace(",", "")) if gross and gross.get("data-value") else None,
        "Movie_Genre": genre.get_text().replace("\n", "").replace('"', "").strip() if genre else None,
        "Director_Star": director.get_text().replace("\n", "").replace("    ", "") if director else None,
    }


def scrape(year: int, count: int) -> tuple[list[dict[str, object]], str | None]:
    """Collect up to count films. The second value is a warning when the listing ends early."""
    session = requests.Session()
    rows: list[dict[str, object]] = []
    start = 1
    seen_ends: set[int] = set()
    skipped = 0
    warning = None

    for page_number in range(1, MAX_PAGES + 1):
        if len(rows) >= count:
            break
        if page_number > 1:
            time.sleep(PAGE_PAUSE_SECONDS)
        url = SEARCH_URL.format(year=year, start=start)
        try:
            soup = fetch_page(session, url)
        except requests.RequestException as error:
            warning = f"Request failed for {url}: {error}."
            break

        cards = soup.find_all("div", {"class": "lister-item-content"})
        if not cards:
            warning = (
                "IMDb did not return the old title-search listing (div.lister-item-content). "
                "The current site markup is different, so this scraper cannot parse the page."
            )
            break

        for card in cards:
            if len(rows) >= count:
                break
            try:
                rows.append(parse_listing(card))
            except (AttributeError, TypeError, ValueError):
                skipped += 1

        end = page_end(soup)
        if end is None or end < start or end in seen_ends:
            warning = "IMDb stopped returning a next page before the requested count."
            break
        seen_ends.add(end)
        start = end + 1
    else:
        warning = f"Stopped after {MAX_PAGES} pages."

    if skipped:
        print(f"Skipped {skipped} listings that did not match the expected card.", file=sys.stderr)
    return rows, warning


def write_csv(rows: list[dict[str, object]], output: Path) -> None:
    """Write the scraped rows. Creates the parent folder."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """Scrape one year and write the CSV."""
    # Step 1
    args = parse_args()

    # Step 2
    try:
        rows, warning = scrape(args.year, args.count)
    except OSError as error:
        fail(f"Could not scrape {args.year}: {error}. Nothing was written.", 1)

    if not rows:
        detail = warning or "No films were parsed."
        fail(f"{detail} Nothing was written to {args.output}.", 1)

    # Step 3
    try:
        write_csv(rows, args.output)
    except OSError as error:
        fail(f"Could not write {args.output}: {error}. The scrape was not saved.", 1)

    print(f"Wrote {len(rows)} films to {args.output}.")
    if warning and len(rows) < args.count:
        fail(
            f"{warning} Wrote {len(rows)} of {args.count} requested rows to {args.output}.",
            1,
        )


if __name__ == "__main__":
    main()
