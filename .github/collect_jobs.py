#!/usr/bin/env python3
"""Collect job-level metadata (conclusion, duration, failed steps) for kgateway's scheduled nightly runs.

Usage: python3 collect_jobs.py OUT.csv --since YYYY-MM-DD
Needs the gh CLI and GH_TOKEN. Writes one row per job of every completed scheduled run.
"""
import csv, json, subprocess, sys
from datetime import datetime

REPO, WORKFLOW = "kgateway-dev/kgateway", "nightly-tests.yaml"


def gh(path):
    return json.loads(subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True).stdout)


def secs(a, b):
    if not a or not b:
        return ""
    f = "%Y-%m-%dT%H:%M:%SZ"
    return int((datetime.strptime(b, f) - datetime.strptime(a, f)).total_seconds())


def main(out, since):
    runs, page = [], 1
    while True:
        batch = gh(f"repos/{REPO}/actions/workflows/{WORKFLOW}/runs?event=schedule&status=completed"
                   f"&created=%3E%3D{since}&per_page=100&page={page}")["workflow_runs"]
        runs += batch
        if len(batch) < 100:
            break
        page += 1
    rows = []
    for run in sorted(runs, key=lambda r: r["created_at"]):
        date = run["created_at"][:10]
        if date < since:
            continue
        try:
            jobs, page = [], 1
            while True:
                b = gh(f"repos/{REPO}/actions/runs/{run['id']}/jobs?per_page=100&page={page}")["jobs"]
                jobs += b
                if len(b) < 100:
                    break
                page += 1
        except subprocess.CalledProcessError as e:
            print(f"WARN: run {run['id']}: {e.stderr.strip()[:150]}")
            continue
        for j in jobs:
            failed = [s["name"] for s in j.get("steps") or [] if s.get("conclusion") == "failure"]
            rows.append({"date": date, "run_id": run["id"], "run_conclusion": run["conclusion"],
                         "head_sha": run["head_sha"], "job_id": j["id"], "job_name": j["name"],
                         "job_conclusion": j["conclusion"], "runner_label": ",".join(j.get("labels") or []),
                         "duration_s": secs(j.get("started_at"), j.get("completed_at")),
                         "failed_steps": " | ".join(failed)})
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(runs)} runs, {len(rows)} jobs")


if __name__ == "__main__":
    a = sys.argv[1:]
    since = a[a.index("--since") + 1] if "--since" in a else "2026-07-23"
    main(a[0], since)
