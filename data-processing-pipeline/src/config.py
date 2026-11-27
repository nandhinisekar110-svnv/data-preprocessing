"""Configuration loading."""
from pathlib import Path

import yaml


def load_config(path: str = "config.yaml") -> dict:
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")
    with cfg_path.open() as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict):
        raise ValueError(f"Config file {cfg_path} is empty or invalid")
    for section in ("input", "output", "cleaning"):
        if section not in cfg:
            raise ValueError(f"Missing '{section}' section in {cfg_path}")
    return cfg
