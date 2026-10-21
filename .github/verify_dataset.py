#!/usr/bin/env python3
"""Check the published dataset against rows re-collected by archive_nightly.py.

For every row of the published CSV, look up the row with the same
(run_id, branch, k8s, validation_mode, routes) in the re-collected CSV and compare all columns.
Rows whose job logs have expired cannot be re-collected and are reported as unavailable.

Usage: python3 verify_dataset.py PUBLISHED.csv RECOLLECTED.csv REPORT.md
"""
import csv, sys
from collections import Counter

KEY = ("run_id", "branch", "k8s", "validation_mode", "routes")


def load(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def main(pub_path, new_path, report_path):
    pub, new = load(pub_path), load(new_path)
    index = {tuple(r[k] for k in KEY): r for r in new}
    new_runs = {r["run_id"] for r in new}
    status, diffs = Counter(), []
    for r in pub:
        k = tuple(r[c] for c in KEY)
        if r["run_id"] not in new_runs:
            status["run not re-collected (log expired or unavailable)"] += 1
        elif k not in index:
            status["row missing from re-collection"] += 1
            diffs.append((k, "row missing", "", ""))
        else:
            bad = [c for c in r if r[c] != index[k].get(c, "")]
            if bad:
                status["row differs"] += 1
                diffs += [(k, c, r[c], index[k].get(c, "")) for c in bad]
            else:
                status["identical"] += 1
    runs_pub = {r["run_id"] for r in pub}
    lines = ["# Re-collection check of the published dataset", "",
             f"Published rows: {len(pub)} from {len(runs_pub)} runs.  ",
             f"Re-collected rows: {len(new)} from {len(new_runs)} runs.  ",
             f"Published runs re-collected: {len(runs_pub & new_runs)} of {len(runs_pub)}.", "",
             "| Outcome | Rows |", "| --- | --- |"]
    lines += [f"| {s} | {n} |" for s, n in sorted(status.items())]
    if diffs:
        lines += ["", "## Differences", "", "| run_id, branch, k8s, mode, routes | column | published | re-collected |",
                  "| --- | --- | --- | --- |"]
        lines += [f"| {', '.join(k)} | {c} | {a} | {b} |" for k, c, a, b in diffs[:300]]
    open(report_path, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines[:12 + len(status)]))


if __name__ == "__main__":
    main(*sys.argv[1:4])
