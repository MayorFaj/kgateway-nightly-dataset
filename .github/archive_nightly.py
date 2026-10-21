#!/usr/bin/env python3
"""Archive kgateway nightly attached-routes load-test results before GitHub deletes the logs.

Runs weekly from .github/workflows/archive-nightly.yaml. For every completed scheduled run of
kgateway-dev/kgateway's nightly workflow that is newer than the newest run already in the CSV,
it downloads each "Load Tests" job log, parses the suite's KEY METRICS blocks and appends one
row per (run, branch, k8s, validation mode, route scale), in the same columns as the published
dataset (Zenodo DOI 10.5281/zenodo.23546846).

Needs: the gh CLI and GH_TOKEN (the workflow's GITHUB_TOKEN is enough for a public repository).
Usage:  python3 archive_nightly.py data/nightly/kgateway_nightly_attachedroutes_live.csv
"""
import csv, json, os, re, subprocess, sys

REPO = "kgateway-dev/kgateway"
WORKFLOW = "nightly-tests.yaml"
START_DATE = "2026-10-21"  # overlaps the last night of the published dataset (21 Oct) to cross-check this parser
COLS = ["date", "run_id", "branch", "k8s", "job_result", "validation_mode", "routes",
        "setup_time", "route_ready_time", "teardown_time", "controller_restart_time",
        "post_restart_translation_time", "status_writes", "test_result"]
METRICS = {
    "Setup Time (Stopwatch)": "setup_time",
    "Route Ready Time": "route_ready_time",
    "Teardown Time": "teardown_time",
    "Controller Restart Time": "controller_restart_time",
    "Post-Restart Translation Check Time": "post_restart_translation_time",
    "Total Writes": "status_writes",
}
TS = re.compile(r"^\S+Z ")                     # Actions timestamp prefix
MODE = re.compile(r"##\[group\]KGateway load tests validation\.level=(\w+)")
METRIC = re.compile(r"attachedroutes_suite\.go:\d+: (Setup Time \(Stopwatch\)|Route Ready Time|Teardown Time|"
                    r"Controller Restart Time|Post-Restart Translation Check Time|Total Writes): (\S+)\s*$")
ROUTES = re.compile(r"attachedroutes_suite\.go:\d+: Routes Tested: (\d+)")
RESULT = re.compile(r"--- (PASS|FAIL): TestKgateway/AttachedRoutes/TestAttachedRoutes(Baseline|Production)\b")
JOB = re.compile(r"Load Tests \(ref=([^,]+), .*k8s=([^)]+)\)")


def gh(path, raw=False):
    out = subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True).stdout
    return out if raw else json.loads(out)


def parse_log(text):
    """Return one dict per KEY METRICS block: mode, routes, the six metrics and the test verdict."""
    mode, current, records = "?", {}, []
    for raw in text.splitlines():
        line = TS.sub("", raw)
        m = MODE.search(line)
        if m:
            mode, current = m.group(1), {}
            continue
        m = METRIC.search(line)
        if m and "TEARDOWN COMPLETE" not in line:
            current[METRICS[m.group(1)]] = m.group(2)
            continue
        m = ROUTES.search(line)
        if m:
            routes = int(m.group(1)) - 1          # "Routes Tested" counts the incremental route
            records.append(dict(current, validation_mode=mode, routes=str(routes), test_result=""))
            current = {}
            continue
        m = RESULT.search(line)
        if m:
            want = "1000" if m.group(2) == "Baseline" else "5000"
            for r in reversed(records):
                if r["validation_mode"] == mode and r["routes"] == want and not r["test_result"]:
                    r["test_result"] = m.group(1)
                    break
    return records


def main(out_path):
    rows = []
    if os.path.exists(out_path):
        with open(out_path, newline="") as f:
            rows = list(csv.DictReader(f))
    seen_runs = {r["run_id"] for r in rows}
    since = max([START_DATE] + [r["date"] for r in rows])
    runs = gh(f"repos/{REPO}/actions/workflows/{WORKFLOW}/runs?event=schedule&status=completed"
              f"&created=%3E%3D{since}&per_page=100")["workflow_runs"]
    added = 0
    for run in sorted(runs, key=lambda r: r["created_at"]):
        if str(run["id"]) in seen_runs:
            continue
        date = run["created_at"][:10]
        jobs = gh(f"repos/{REPO}/actions/runs/{run['id']}/jobs?per_page=100")["jobs"]
        for job in jobs:
            m = JOB.match(job["name"])
            if not m or job["status"] != "completed":
                continue
            branch, k8s = m.groups()
            try:
                text = gh(f"repos/{REPO}/actions/jobs/{job['id']}/logs", raw=True)
            except subprocess.CalledProcessError as e:
                print(f"WARN: no log for job {job['id']} ({job['name']}): {e.stderr.strip()[:200]}")
                continue
            keys = set()
            for rec in parse_log(text):
                key = (rec["validation_mode"], rec["routes"])
                if key in keys:
                    continue                      # summaries can be printed twice; keep the first
                keys.add(key)
                rows.append({"date": date, "run_id": str(run["id"]), "branch": branch, "k8s": k8s,
                             "job_result": job["conclusion"] or "", **{c: rec.get(c, "") for c in COLS[5:]}})
                added += 1
    rows.sort(key=lambda r: (r["date"], r["run_id"], r["branch"], r["k8s"], r["validation_mode"], int(r["routes"] or 0)))
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"added {added} rows; {len(rows)} rows total; newest run date {rows[-1]['date'] if rows else '-'}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/nightly/kgateway_nightly_attachedroutes_live.csv")
