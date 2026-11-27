# Data Processing Pipeline

A configurable Python pipeline that reads raw data (CSV, JSON or a REST API), cleans and
transforms it with pandas, and writes structured results plus a summary report.

## Features

- **Inputs:** CSV, JSON (list of records or `{"data": [...]}`), or an HTTP API returning JSON
- **Cleaning:** column-name normalisation, whitespace trimming, placeholder detection
  (`N/A`, `null`, `-`), type conversion (int / float / date / str), currency-symbol stripping,
  mixed date formats
- **Missing values:** drop rows missing required fields, fill defaults, fill numerics with the median
- **Edge cases:** empty file, missing file, malformed CSV rows, unparseable values, duplicates,
  negative quantities / prices, invalid emails, missing columns
- **Logging:** console + rotating-friendly file log (`logs/pipeline.log`)
- **Config management:** everything lives in `config.yaml`; CLI flags can override paths
- **Tests:** pytest suite covering each cleaning rule and an end-to-end run

## Project structure

```
.
├── config.yaml            # all settings
├── requirements.txt
├── src/
│   ├── main.py            # CLI entry point
│   ├── config.py          # YAML loading + validation
│   ├── logger.py          # logging setup
│   ├── readers.py         # CSV / JSON / API readers
│   ├── cleaning.py        # cleaning + transformation rules
│   └── writers.py         # CSV / JSON output + summary report
├── data/
│   ├── sample_input.csv   # messy example input
│   ├── sample_output.csv  # cleaned result
│   └── summary.json       # what the pipeline changed
└── tests/test_cleaning.py
```

## Setup

Requires Python 3.10+.

```bash
git clone https://github.com/<your-username>/<repo>.git
cd <repo>
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
# run with the defaults in config.yaml
python -m src.main

# override paths
python -m src.main --input data/sample_input.csv --output out/clean.csv --summary out/summary.json

# use a different config file
python -m src.main --config my_config.yaml
```

Exit codes: `0` success, `1` input/processing error, `2` config error.

To read from JSON or an API, set `input.format` to `json` or `api` (and `input.api_url`) in `config.yaml`.

## Configuration (`config.yaml`)

| Key | Purpose |
|-----|---------|
| `input.format` / `input.path` / `input.api_url` | Where the data comes from |
| `output.format` / `output.path` / `output.summary_path` | Where results go (`csv` or `json`) |
| `cleaning.schema` | Column → target type (`int`, `float`, `str`, `date`) |
| `cleaning.required` | Rows missing any of these are dropped |
| `cleaning.drop_duplicates_on` | Key columns for de-duplication (last record wins) |
| `cleaning.fill_defaults` | Constant fill values for missing data |
| `cleaning.fill_median` | Numeric columns filled with their median |
| `cleaning.na_tokens` | Strings treated as missing |
| `logging.level` / `logging.file` | Log verbosity and log file path |

## Sample data

`data/sample_input.csv` has 11 deliberately messy rows: mixed-case names, a `$1,250.00` price,
`N/A` and `null` tokens, a US-style date, an unparseable date, a duplicate order, a missing order ID,
a negative quantity and a non-numeric price.

The pipeline turns it into 7 clean rows (`data/sample_output.csv`) and records what it did in
`data/summary.json`: 2 rows dropped for missing required fields, 1 duplicate removed,
1 row dropped for a negative quantity, and several values filled.

## Design decisions

- **Everything is read as strings first.** Type conversion happens in one place, so bad values
  are counted and logged instead of crashing the read.
- **Dropped vs. fixed.** Missing identifiers and dates can't be guessed, so those rows are dropped.
  Missing prices are filled with the median; missing quantity defaults to 1.
- **Duplicates keep the last record**, assuming later rows are corrections.
- **Config over code.** Changing the schema, defaults or paths never requires touching Python.
- **Derived field:** `total_price = quantity * unit_price`.

## Running tests

```bash
pytest -q
```
