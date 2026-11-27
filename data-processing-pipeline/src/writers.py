"""Output writers."""
import json
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger("pipeline.writers")


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%d")
    return out


def write_output(df: pd.DataFrame, cfg: dict) -> Path:
    path = Path(cfg["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    fmt = str(cfg.get("format", "csv")).lower()
    out = _prepare(df)
    if fmt == "csv":
        out.to_csv(path, index=False)
    elif fmt == "json":
        out.to_json(path, orient="records", indent=2)
    else:
        raise ValueError(f"Unsupported output format: {fmt}")
    log.info("Wrote %d rows to %s", len(out), path)
    return path


def write_summary(stats: dict, path: str | None) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(stats, indent=2))
    log.info("Wrote summary to %s", p)
