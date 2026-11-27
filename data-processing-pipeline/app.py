"""Streamlit web demo for the data processing pipeline.

Run locally:  streamlit run app.py
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.cleaning import clean
from src.config import load_config
from src.readers import InputError, _records_to_df
from src.writers import _prepare

ROOT = Path(__file__).parent
CFG = load_config(str(ROOT / "config.yaml"))
SAMPLE = ROOT / "data" / "sample_input.csv"

st.set_page_config(page_title="Data Processing Pipeline", page_icon="🧹", layout="wide")
st.title("🧹 Data Processing Pipeline")
st.caption("Upload a messy CSV or JSON file. The pipeline cleans it, converts types, "
           "handles missing values and edge cases, and shows exactly what changed.")


def load(file) -> pd.DataFrame:
    name = file.name.lower()
    if name.endswith(".json"):
        try:
            return _records_to_df(json.load(file))
        except json.JSONDecodeError as exc:
            raise InputError(f"Invalid JSON: {exc}") from exc
    try:
        return pd.read_csv(file, dtype=str, on_bad_lines="skip", skipinitialspace=True)
    except pd.errors.EmptyDataError as exc:
        raise InputError("The file is empty.") from exc


with st.sidebar:
    st.header("Input")
    uploaded = st.file_uploader("Upload CSV or JSON", type=["csv", "json"])
    use_sample = st.checkbox("Use the sample dataset", value=uploaded is None)
    st.markdown("**Expected columns:** " + ", ".join(f"`{c}`" for c in CFG["cleaning"]["schema"]))
    st.caption("Rules (required fields, defaults, dedupe key) come from `config.yaml`.")

try:
    if uploaded is not None:
        raw = load(uploaded)
    elif use_sample:
        raw = pd.read_csv(SAMPLE, dtype=str)
    else:
        st.info("Upload a file or tick 'Use the sample dataset' to begin.")
        st.stop()
    if raw.empty:
        raise InputError("The input contains no rows.")
    cleaned, stats = clean(raw, CFG["cleaning"])
except InputError as exc:
    st.error(f"Input error: {exc}")
    st.stop()
except Exception as exc:
    st.error(f"Pipeline failed: {exc}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows in", stats["rows_in"])
c2.metric("Rows out", stats["rows_out"])
c3.metric("Dropped", stats["rows_in"] - stats["rows_out"])
c4.metric("Values filled", sum(stats["filled_values"].values()))

left, right = st.columns(2)
with left:
    st.subheader("Raw input")
    st.dataframe(raw, width="stretch")
with right:
    st.subheader("Cleaned output")
    out = _prepare(cleaned)
    st.dataframe(out, width="stretch")

st.subheader("What the pipeline did")
st.json(stats)

d1, d2 = st.columns(2)
d1.download_button("⬇️ Download cleaned CSV", out.to_csv(index=False), "cleaned_output.csv", "text/csv")
d2.download_button("⬇️ Download summary JSON", json.dumps(stats, indent=2), "summary.json", "application/json")
