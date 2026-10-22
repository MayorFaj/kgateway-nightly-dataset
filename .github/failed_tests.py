#!/usr/bin/env python3
"""For every failed "Load Tests" job in kgateway_nightly_jobs.csv, list the Go tests that failed.

Usage: python3 failed_tests.py JOBS.csv OUT.csv   (needs gh CLI and GH_TOKEN)
"""
import csv, os, re, subprocess, sys

REPO = "kgateway-dev/kgateway"
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
FAIL = re.compile(r"--- FAIL: (\S+)")
PANIC = re.compile(r"panic: (.{0,120})")


def log(job_id):
    path = f"repos/{REPO}/actions/jobs/{job_id}/logs"
    try:
        out = subprocess.run(["gh", "api", "--allow-escape-sequences", path], check=True, capture_output=True, text=True).stdout
    except subprocess.CalledProcessError:
        out = subprocess.run(["curl", "-sSfL", "-H", f"Authorization: Bearer {os.environ['GH_TOKEN']}",
                              f"https://api.github.com/{path}"], check=True, capture_output=True, text=True).stdout
    return ANSI.sub("", out)


def main(jobs_csv, out_csv):
    rows = []
    for j in csv.DictReader(open(jobs_csv)):
        if not j["job_name"].startswith("Load Tests") or j["job_conclusion"] != "failure":
            continue
        try:
            text = log(j["job_id"])
            fails = sorted(set(FAIL.findall(text)))
            panics = sorted(set(PANIC.findall(text)))[:3]
            status = "ok"
        except subprocess.CalledProcessError:
            fails, panics, status = [], [], "log unavailable"
        rows.append({"date": j["date"], "job_id": j["job_id"], "job_name": j["job_name"], "log": status,
                     "failed_tests": " | ".join(fails), "panics": " | ".join(panics)})
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "job_id", "job_name", "log", "failed_tests", "panics"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} failed load-test jobs")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
