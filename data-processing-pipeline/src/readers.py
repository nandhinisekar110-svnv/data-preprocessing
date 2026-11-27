"""Readers for CSV, JSON and API sources."""
import json
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger("pipeline.readers")


class InputError(Exception):
    """Raised when the input cannot be read or is empty."""


def _records_to_df(data) -> pd.DataFrame:
    """Accept a list of records or a dict wrapping one (e.g. {"data": [...]})."""
    if isinstance(data, dict):
        lists = [v for v in data.values() if isinstance(v, list)]
        data = lists[0] if lists else [data]
    if not isinstance(data, list):
        raise InputError("JSON must contain a list of records")
    return pd.json_normalize(data)


def read_csv(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise InputError(f"Input file not found: {p}")
    try:
        # dtype=str: we do our own type conversion so bad values are counted, not crashed on
        return pd.read_csv(p, dtype=str, on_bad_lines="skip", skipinitialspace=True)
    except pd.errors.EmptyDataError as exc:
        raise InputError(f"Input file is empty: {p}") from exc


def read_json(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise InputError(f"Input file not found: {p}")
    try:
        with p.open() as fh:
            return _records_to_df(json.load(fh))
    except json.JSONDecodeError as exc:
        raise InputError(f"Invalid JSON in {p}: {exc}") from exc


def read_api(url: str, timeout: int = 15) -> pd.DataFrame:
    import requests

    if not url:
        raise InputError("input.api_url is required when format is 'api'")
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return _records_to_df(resp.json())
    except (requests.RequestException, ValueError) as exc:
        raise InputError(f"API request failed: {exc}") from exc


def read_input(cfg: dict) -> pd.DataFrame:
    fmt = str(cfg.get("format", "csv")).lower()
    log.info("Reading input (format=%s)", fmt)
    if fmt == "csv":
        df = read_csv(cfg["path"])
    elif fmt == "json":
        df = read_json(cfg["path"])
    elif fmt == "api":
        df = read_api(cfg.get("api_url"), cfg.get("api_timeout_seconds", 15))
    else:
        raise InputError(f"Unsupported input format: {fmt}")
    if df.empty:
        raise InputError("Input contains no rows")
    log.info("Read %d rows, %d columns", len(df), len(df.columns))
    return df
