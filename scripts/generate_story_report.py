"""Report for one story suite, in the same format as the full report (summary first page, plain scenario sentences,
raw pytest output in a side file).

Run: python -m scripts.generate_story_report no_barcode|close_bag|two_lines|health_check|postal_contracts
"""

from __future__ import annotations

import sys
import time
from datetime import datetime

import scripts.generate_full_report as full

# marker = the pytest marker of the story; folder = what to collect it from.
STORIES = {
    "no_barcode": {
        "folder": "tests/3_destination/test_no_barcode.py",
        "title": "Report: parcels without a barcode, special chutes and re-reads",
        "label": "no barcode",
    },
    "close_bag": {
        "folder": "tests/4_bagging/test_close_bag.py",
        "title": "Report: closing a bag, serviceTypes, Pending monitoring and the emergency option",
        "label": "close bag",
    },
    "two_lines": {
        "folder": "tests/1_device_lifecycle/test_two_lines.py",
        "title": "Report: a center with two sorting lines",
        "label": "two lines",
    },
    "health_check": {
        "folder": "tests/1_device_lifecycle/test_health_check.py",
        "title": "Report: connection health check (connectivity.check)",
        "label": "health check",
    },
    "postal_contracts": {
        "folder": "tests/4_bagging",
        "title": "Report: Postal error-code preservation and Mock status",
        "label": "postal contracts",
    },
}
STORY_TIMEOUT_SECONDS = 3600


def main(story: str) -> int:
    config = STORIES[story]
    full.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    # The full report's domain table is how a suite gets its name; a story is one extra suite.
    full.DOMAINS[story] = {"name": config["label"], "folder": config["folder"], "markers": (story,)}
    try:  # the same check the full report makes: which center and device this run is about
        full.os.environ["REPORT_PRIMARY_CENTER"] = full.prepare_primary_device_profile()["center"]
    except RuntimeError as error:
        print(f"  Primary device not verified ({error}); the report will say so.", flush=True)
    started = datetime.now()
    clock = time.perf_counter()
    run = full.run_domain(story, config["folder"], story, timeout=STORY_TIMEOUT_SECONDS)
    elapsed = round(time.perf_counter() - clock, 1)
    results = {story: full.combine_results(run)}
    path = full.REPORT_DIR / f"{story.upper()}_Report_{started:%Y%m%d_%H%M%S}.html"
    full.write_report_checkpoint(path, results, f"{started:%Y-%m-%d %H:%M:%S}", elapsed, full.collect_report_metadata(),
                                 title=config["title"])
    print(f"  {config['label']}: {run['passed']} passed, {run['failed']} failed, {run['skipped']} skipped")
    print(f"  HTML Report: {path}")
    return 1 if run["failed"] or run["errors"] else 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) != 2 or sys.argv[1] not in STORIES:
        sys.exit(f"usage: python -m scripts.generate_story_report {'|'.join(STORIES)}")
    sys.exit(main(sys.argv[1]))
