"""Cleaning and transformation logic."""
import logging
import re

import pandas as pd

log = logging.getLogger("pipeline.cleaning")

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
DEFAULT_NA = ["", "na", "n/a", "null", "none", "nan", "-"]


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df


def _normalize_strings(df: pd.DataFrame, na_tokens: list[str]) -> pd.DataFrame:
    """Strip whitespace and turn placeholder tokens (N/A, null, -, ...) into real NA."""
    tokens = {t.lower() for t in na_tokens}
    for col in df.columns:
        s = df[col].astype("string").str.strip()
        df[col] = s.mask(s.str.lower().isin(tokens))
    return df


def _convert_types(df: pd.DataFrame, schema: dict, stats: dict) -> pd.DataFrame:
    unconvertible = {}
    for col, typ in schema.items():
        if col not in df.columns:
            log.warning("Column '%s' missing from input; created empty", col)
            df[col] = pd.Series([pd.NA] * len(df), dtype="string")
        before = int(df[col].notna().sum())
        if typ in ("int", "float"):
            text = df[col].astype("string").str.replace(r"[,$\s]", "", regex=True)
            num = pd.to_numeric(text, errors="coerce")
            df[col] = num.round().astype("Int64") if typ == "int" else num.astype("Float64")
        elif typ == "date":
            df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed")
        else:
            df[col] = df[col].astype("string")
        lost = before - int(df[col].notna().sum())
        if lost:
            unconvertible[col] = lost
            log.warning("Column '%s': %d value(s) could not be converted to %s", col, lost, typ)
    stats["unconvertible_values"] = unconvertible
    return df


def clean(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    """Run the full cleaning pipeline. Returns (clean_df, stats)."""
    stats: dict = {"rows_in": int(len(df))}

    df = _normalize_columns(df)
    df = _normalize_strings(df, cfg.get("na_tokens", DEFAULT_NA))
    df = _convert_types(df, cfg.get("schema", {}), stats)

    # 1. drop rows missing required fields
    required = [c for c in cfg.get("required", []) if c in df.columns]
    n = len(df)
    df = df.dropna(subset=required)
    stats["dropped_missing_required"] = n - len(df)

    # 2. de-duplicate (keep the most recent record)
    dedupe = [c for c in cfg.get("drop_duplicates_on", []) if c in df.columns]
    n = len(df)
    if dedupe:
        df = df.drop_duplicates(subset=dedupe, keep="last")
    stats["dropped_duplicates"] = n - len(df)

    # 3. fill missing values
    filled = {}
    for col, value in cfg.get("fill_defaults", {}).items():
        if col in df.columns:
            count = int(df[col].isna().sum())
            if count:
                df[col] = df[col].fillna(value)
                filled[col] = count
    for col in cfg.get("fill_median", []):
        if col in df.columns and df[col].isna().any():
            median = df[col].median()
            if pd.isna(median):
                continue  # whole column empty; nothing sensible to fill with
            median = round(float(median), 2)
            filled[col] = int(df[col].isna().sum())
            df[col] = df[col].fillna(median)
    stats["filled_values"] = filled

    # 4. validation rules
    n = len(df)
    if "quantity" in df.columns:
        df = df[df["quantity"].isna() | (df["quantity"] > 0)]
    if "unit_price" in df.columns:
        df = df[df["unit_price"].isna() | (df["unit_price"] >= 0)]
    stats["dropped_invalid_values"] = n - len(df)

    df = df.copy()
    if "email" in df.columns:
        df["email"] = df["email"].str.lower()
        bad = df["email"].notna() & ~df["email"].fillna("").str.match(EMAIL_RE)
        stats["invalid_emails_nulled"] = int(bad.sum())
        df.loc[bad, "email"] = pd.NA

    # 5. standardise text + derived column
    if "customer_name" in df.columns:
        df["customer_name"] = df["customer_name"].str.title()
    if "country" in df.columns:
        # short codes (USA, UK) stay upper-case, everything else is title-cased
        df["country"] = df["country"].map(
            lambda v: v if pd.isna(v) else (v.upper() if len(v) <= 3 else v.title())
        )
    if {"quantity", "unit_price"} <= set(df.columns):
        df["total_price"] = (df["quantity"] * df["unit_price"]).round(2)

    sort_col = required[0] if required else df.columns[0]
    df = df.sort_values(sort_col).reset_index(drop=True)
    stats["rows_out"] = int(len(df))
    log.info("Cleaning done: %d -> %d rows", stats["rows_in"], stats["rows_out"])
    return df, stats
