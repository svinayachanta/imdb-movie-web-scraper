# IMDb movie trends, 2014–2021

Scrapes IMDb and looks at revenue, votes, ratings, and genre. Built with Aashay Maheshwarkar and Megh KC.

## Data

`01-scrape.py` pulls title, year, genre, rating, metascore, votes, gross, director, and stars with Beautiful Soup. The year files `datasets/movies-2014.csv` through `datasets/movies-2021.csv` are already scraped, so the analysis scripts do not call IMDb. `datasets/movies-2022.csv` is an extra extract. The merge stops at 2021, which is the range in the write-up.

`02-prepare.py` stacks those year files and writes `datasets/movies-clean.csv`. Each year file has 10,000 rows, and about 93% have no Metascore. The clean table keeps the 4,779 films with a year, rating, Metascore, votes, gross, genre, and director. Votes, rating, Metascore, and gross are numbers. The director and stars are split into their own columns.

`datasets/inflation.csv` adjusts gross to 2023 dollars in the rating and genre scripts.

## What the analysis checks

1. `03-gross-by-year.py` sums US gross by year.
2. `04-votes-vs-box-office.py` plots votes against box office and runs a Pearson test.
3. `05-rating-vs-box-office.py` does the same for IMDb rating, after adjusting gross and repeating a film once per genre.
4. `06-genre-share.py` shows each genre's share of mean inflation-adjusted gross.
5. `07-director-ratings.py` is a t-test of ratings for two directors, with a density plot.

## Results

Reported US gross is about $10–11 billion a year from 2014 through 2019. It drops to about $1.2 billion in 2020 and is about $3.6 billion in 2021. That chart is the scraped gross, not the inflation-adjusted gross used in the rating and genre checks.

Votes and box office move together. The Pearson statistic is 0.73 and the p-value is about 0. Commercial movies collect more votes.

Rating and box office also move together, more moderately. The Pearson statistic from `05-rating-vs-box-office.py` is 0.59 and the p-value is about 0. The written report records 0.56 for the same check.

Adventure takes the largest share of box office, then animation.

Tyler Perry's films in the sample average 5.01 (standard deviation 0.72). Christopher Nolan's average 7.90 (standard deviation 0.65). The t statistic is -5.90 and the p-value is about 0, so the two means differ.

## Run

From this folder:

```bash
pip install -r requirements.txt
python 02-prepare.py
python 03-gross-by-year.py
python 04-votes-vs-box-office.py
python 05-rating-vs-box-office.py
python 06-genre-share.py
python 07-director-ratings.py
```

Charts are written to `figures/`. `01-scrape.py` is only for a fresh IMDb extract. Pass `--output` with the CSV path you want.
