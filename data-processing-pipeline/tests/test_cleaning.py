import json

import pandas as pd
import pytest

from src.cleaning import clean
from src.config import load_config
from src.main import run
from src.readers import InputError, read_csv

CFG = load_config("config.yaml")["cleaning"]


def make(rows):
    return pd.DataFrame(rows, dtype=str)


def test_drops_rows_missing_required():
    df = make([{"Order ID": None, "Order Date": "2026-01-01"},
               {"Order ID": "1", "Order Date": "2026-01-01"}])
    out, stats = clean(df, CFG)
    assert len(out) == 1 and stats["dropped_missing_required"] == 1


def test_duplicates_keep_last():
    df = make([{"Order ID": "1", "Order Date": "2026-01-01", "Unit Price": "5"},
               {"Order ID": "1", "Order Date": "2026-01-01", "Unit Price": "9"}])
    out, stats = clean(df, CFG)
    assert len(out) == 1 and out.loc[0, "unit_price"] == 9 and stats["dropped_duplicates"] == 1


def test_type_conversion_and_currency_symbols():
    df = make([{"Order ID": "1", "Order Date": "2026-01-01", "Quantity": "2", "Unit Price": "$1,250.50"}])
    out, _ = clean(df, CFG)
    assert out.loc[0, "unit_price"] == 1250.50 and out.loc[0, "total_price"] == 2501.00


def test_defaults_and_median_fill():
    df = make([{"Order ID": "1", "Order Date": "2026-01-01", "Unit Price": "10"},
               {"Order ID": "2", "Order Date": "2026-01-02", "Unit Price": "20"},
               {"Order ID": "3", "Order Date": "2026-01-03", "Unit Price": "N/A", "Country": "-"}])
    out, _ = clean(df, CFG)
    assert out.loc[2, "unit_price"] == 15 and out.loc[2, "country"] == "Unknown"
    assert (out["quantity"] == 1).all()


def test_invalid_values_dropped_and_bad_email_nulled():
    df = make([{"Order ID": "1", "Order Date": "2026-01-01", "Quantity": "-3", "Email": "x@y.com"},
               {"Order ID": "2", "Order Date": "2026-01-02", "Quantity": "1", "Email": "bad@email"}])
    out, stats = clean(df, CFG)
    assert len(out) == 1 and pd.isna(out.loc[0, "email"]) and stats["invalid_emails_nulled"] == 1


def test_unparseable_date_row_is_dropped():
    out, _ = clean(make([{"Order ID": "1", "Order Date": "garbage"}]), CFG)
    assert out.empty


def test_empty_file_raises(tmp_path):
    f = tmp_path / "empty.csv"
    f.write_text("")
    with pytest.raises(InputError):
        read_csv(str(f))


def test_missing_file_returns_error_code(tmp_path):
    assert run("config.yaml", input_path=str(tmp_path / "nope.csv"),
               output_path=str(tmp_path / "o.csv")) == 1


def test_end_to_end(tmp_path):
    out, summary = tmp_path / "out.csv", tmp_path / "summary.json"
    assert run("config.yaml", output_path=str(out), summary_path=str(summary)) == 0
    df = pd.read_csv(out)
    assert df["order_id"].is_unique and len(df) > 0
    assert json.loads(summary.read_text())["rows_out"] == len(df)
