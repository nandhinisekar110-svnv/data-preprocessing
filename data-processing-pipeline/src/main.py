"""CLI entry point:  python -m src.main --config config.yaml"""
import argparse
import sys

from src.cleaning import clean
from src.config import load_config
from src.logger import setup_logging
from src.readers import InputError, read_input
from src.writers import write_output, write_summary


def run(config_path: str, input_path: str | None = None, output_path: str | None = None,
        summary_path: str | None = None) -> int:
    try:
        cfg = load_config(config_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2

    log = setup_logging(cfg.get("logging"))
    if input_path:
        cfg["input"]["path"] = input_path
    if output_path:
        cfg["output"]["path"] = output_path
    if summary_path:
        cfg["output"]["summary_path"] = summary_path

    try:
        raw = read_input(cfg["input"])
        df, stats = clean(raw, cfg["cleaning"])
        write_output(df, cfg["output"])
        write_summary(stats, cfg["output"].get("summary_path"))
    except InputError as exc:
        log.error("Input error: %s", exc)
        return 1
    except Exception:  # last-resort guard so failures are logged with a traceback
        log.exception("Pipeline failed unexpectedly")
        return 1

    log.info("Pipeline finished successfully")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Data processing pipeline")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--input", help="override input path")
    parser.add_argument("--output", help="override output path")
    parser.add_argument("--summary", help="override summary path")
    args = parser.parse_args()
    sys.exit(run(args.config, args.input, args.output, args.summary))


if __name__ == "__main__":
    main()
