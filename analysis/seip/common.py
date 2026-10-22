"""Shared helpers: load the measurements and convert Go duration strings to seconds."""
import csv, os, re
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
LIVE = os.path.join(ROOT, "data", "nightly", "kgateway_nightly_attachedroutes_live.csv")
PUB = os.path.join(ROOT, "kgateway_nightly_attachedroutes_dedup.csv")


def sec(v):
    if not v:
        return None
    m = re.fullmatch(r"(?:(\d+)m)?([\d.]+)(ms|s|µs)", v)
    return float(m.group(2)) * {"ms": 1e-3, "s": 1, "µs": 1e-6}[m.group(3)] + 60 * int(m.group(1) or 0)


def load(path=LIVE):
    rows = list(csv.DictReader(open(path)))
    for r in rows:
        for c in ["setup_time", "route_ready_time", "teardown_time", "controller_restart_time", "post_restart_translation_time"]:
            r[c + "_s"] = sec(r[c])
    return rows


def pct(x, q):
    return float(np.percentile(x, q))
