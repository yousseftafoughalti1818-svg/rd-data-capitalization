"""Full pipeline: inventory -> extraction -> normalization -> database -> quality report.

Usage:
    python -m rdcap.pipeline
"""
from __future__ import annotations

import logging

from rdcap import config
from rdcap.inventory import build_inventory
from rdcap.load import load_all
from rdcap.quality import run_quality_checks, write_report

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("rdcap.pipeline")


def run(raw_dir=None, db_path=None) -> dict:
    raw_dir = raw_dir or config.RAW_DIR
    db_path = db_path or config.DB_PATH
    inventory = build_inventory(raw_dir)
    log.info("Inventory: %d files", len(inventory))
    counts = load_all(inventory, raw_dir, db_path)
    issues = run_quality_checks(db_path)
    write_report(issues, counts, inventory)
    log.info("%d issues detected - see reports/quality_report.md", len(issues))
    return {**counts, "issues": len(issues)}


if __name__ == "__main__":
    run()
