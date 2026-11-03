"""History-aware regression check for kgateway's nightly control-plane scale tests.

Compares each night with the nights before it and raises an alarm when a metric gets
persistently worse. Validated three ways on the published nightly data:

  1. backtest: alarms on the real, unmodified series (candidate regressions / false alarms)
  2. injected slowdowns: realistic step slowdowns added to the real data at random nights
  3. comparison with the suite's fixed pass/fail limits, a naive one-night relative gate,
     and E-divisive change-point detection (analysis/seip/edivisive.py)

Parameters of the proposed check were fixed before any results were computed:
  WINDOW=14 nights, K=3 robust deviations, MIN_REL=5%, CONSECUTIVE=2 nights.

Usage:  python3 regression_check.py [path/to/kgateway_nightly_attachedroutes_live.csv]
Writes results.json and results.md next to this script.
"""
import json, os, sys, time
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "seip"))
from common import load, LIVE  # noqa: E402
from edivisive import e_divisive  # noqa: E402

# ---- pre-specified parameters --------------------------------------------------------
WINDOW, K, MIN_REL, CONSECUTIVE = 14, 3.0, 0.05, 2
STEP = {"setup_time_s": 1.0, "teardown_time_s": 0.1, "controller_restart_time_s": 0.5}  # polling intervals
FIXED_LIMIT = {("setup_time_s", "1000"): 30, ("setup_time_s", "5000"): 90,
               ("teardown_time_s", "1000"): 10, ("teardown_time_s", "5000"): 20}
BRANCHES = ["main", "v2.4.x"]          # the two branches with every metric for the whole period
METRICS = ["setup_time_s", "teardown_time_s", "controller_restart_time_s"]
SCALES = ["1000", "5000"]
SLOWDOWNS = [0.05, 0.10, 0.20, 0.50, 1.00]
TRIALS = 200                            # per series x slowdown for the online gates
ED_TRIALS, ED_PERMS = 40, 99            # E-divisive is expensive: fewer trials
HORIZON = 10                            # nights allowed for detection after the slowdown starts
SEED = 20261103


# ---- data -----------------------------------------------------------------------------
def nightly_rows(R, b, col, sc):
    """dict date -> list of raw values (successful measurements only)."""
    d = defaultdict(list)
    for r in R:
        if r["branch"] == b and r["routes"] == sc and r[col] is not None:
            d[r["date"]].append(r[col])
    return dict(sorted(d.items()))


def medians(night_lists):
    return np.array([np.median(v) for v in night_lists])


def inject(night_lists, start, slowdown, step, rng):
    """Apply a persistent slowdown from night `start` on, respecting the polling grid.
    An observed value v means the true latency was in (v - step, v]; draw it uniformly,
    scale it, and re-observe it at the next poll."""
    out = []
    for j, vals in enumerate(night_lists):
        if j < start:
            out.append(vals)
            continue
        new = []
        for v in vals:
            true = v - rng.uniform(0, step)
            slow = true * (1 + slowdown)
            new.append(v + np.ceil((slow - v) / step - 1e-9) * step if slow > v else v)
        out.append(new)
    return out


# ---- detectors (each returns list of alarm night indices) ----------------------------
def robust_gate(y, step, direction=+1):
    alarms, run = [], 0
    floor = 0.25 * step
    for i in range(WINDOW, len(y)):
        hist = y[i - WINDOW:i]
        base = np.median(hist)
        spread = max(1.4826 * np.median(np.abs(hist - base)), floor)
        if direction > 0:
            bad = y[i] > base + K * spread and y[i] > base * (1 + MIN_REL)
        else:
            bad = y[i] < base - K * spread and y[i] < base * (1 - MIN_REL)
        run = run + 1 if bad else 0
        if run == CONSECUTIVE:
            alarms.append(i)
    return alarms


def naive_gate(y, k=1.5, w=7):
    return [i for i in range(w, len(y)) if y[i] > k * np.median(y[i - w:i])]


def fixed_gate(night_lists, limit):
    if limit is None:
        return []
    return [i for i, vals in enumerate(night_lists) if max(vals) > limit]


# ---- main -----------------------------------------------------------------------------
def main(path):
    t0 = time.time()
    R = load(path)
    rng = np.random.default_rng(SEED)
    series = {}
    for b in BRANCHES:
        for col in METRICS:
            for sc in SCALES:
                nl = nightly_rows(R, b, col, sc)
                if len(nl) >= 40:
                    series[(b, col, sc)] = (list(nl.keys()), list(nl.values()))
    out = dict(parameters=dict(window=WINDOW, k=K, min_rel=MIN_REL, consecutive=CONSECUTIVE,
                               trials=TRIALS, ed_trials=ED_TRIALS, horizon=HORIZON, seed=SEED),
               data=dict(file=os.path.relpath(path, HERE), first=min(d for k in series for d in series[k][0]),
                         last=max(d for k in series for d in series[k][0])),
               series={}, backtest={}, injection=[], known_change={}, reliability={})

    # 1. backtest on real data
    total_nights = 0
    for key, (ds, nl) in series.items():
        b, col, sc = key
        y = medians(nl)
        total_nights += len(y) - WINDOW
        out["series"]["|".join(key)] = dict(nights=len(y), median=round(float(np.median(y)), 3),
                                           cv=round(float(np.std(y) / np.mean(y)), 3))
        rob = robust_gate(y, STEP[col])
        nai = naive_gate(y)
        fix = fixed_gate(nl, FIXED_LIMIT.get((col, sc)))
        out["backtest"]["|".join(key)] = dict(
            robust=[(ds[i], round(float(y[i]), 3), round(float(np.median(y[i - WINDOW:i])), 3)) for i in rob],
            naive=len(nai), fixed=len(fix))
    out["backtest_summary"] = dict(
        series_nights=total_nights,
        robust_alarms=sum(len(v["robust"]) for v in out["backtest"].values()),
        naive_alarms=sum(v["naive"] for v in out["backtest"].values()),
        fixed_alarms=sum(v["fixed"] for v in out["backtest"].values()))

    # 2. the known real change: main 5,000-route teardown, PR #14519 (13 Aug 2026), an improvement
    ds, nl = series[("main", "teardown_time_s", "5000")]
    y = medians(nl)
    i0 = ds.index("2026-08-13")
    imp = [i for i in robust_gate(y, STEP["teardown_time_s"], direction=-1) if i >= i0]
    out["known_change"] = dict(event="PR #14519 teardown improvement, main, 5,000 routes", start=ds[i0],
                               robust_first_alarm=ds[imp[0]] if imp else None,
                               robust_delay_nights=(imp[0] - i0 + 1) if imp else None,
                               before_median=round(float(np.median(y[i0 - WINDOW:i0])), 3),
                               after_median=round(float(np.median(y[i0:i0 + WINDOW])), 3))

    # 3. injected slowdowns
    # A "hit" is any alarm in the HORIZON nights from the start of the slowdown. Some of those
    # alarms would have fired anyway, so each detector is also scored on the UNMODIFIED series
    # over the same windows ("chance"); "net" = hit rate minus chance rate.
    def in_window(alarms, start):
        return any(start <= i < start + HORIZON for i in alarms)

    for key, (ds, nl) in series.items():
        b, col, sc = key
        step, limit = STEP[col], FIXED_LIMIT.get((col, sc))
        n = len(nl)
        y0 = medians(nl)
        base_alarms = dict(robust=robust_gate(y0, step), naive=naive_gate(y0), fixed=fixed_gate(nl, limit))
        base_cps = [c for c, _ in e_divisive(y0, perms=ED_PERMS, seed=0)]
        for d in SLOWDOWNS:
            hits = dict(robust=0, naive=0, fixed=0, edivisive=0)
            chance = dict(robust=0, naive=0, fixed=0, edivisive=0)
            delays, ed_n = [], 0
            for t in range(TRIALS):
                start = int(rng.integers(WINDOW + 5, n - HORIZON))
                inj = inject(nl, start, d, step, rng)
                y = medians(inj)
                rob = robust_gate(y, step)
                hit = [i for i in rob if start <= i < start + HORIZON]
                if hit:
                    hits["robust"] += 1
                    delays.append(hit[0] - start + 1)
                hits["naive"] += in_window(naive_gate(y), start)
                hits["fixed"] += in_window(fixed_gate(inj, limit), start)
                for k in ("robust", "naive", "fixed"):
                    chance[k] += in_window(base_alarms[k], start)
                if t < ED_TRIALS:   # retrospective change-point detection on the full injected series
                    ed_n += 1
                    cps = e_divisive(y, perms=ED_PERMS, seed=t)
                    hits["edivisive"] += any(abs(c - start) <= 2 for c, _ in cps)
                    chance["edivisive"] += any(abs(c - start) <= 2 for c in base_cps)
            row = dict(series="|".join(key), slowdown=d,
                       robust_median_delay=float(np.median(delays)) if delays else None)
            for k in hits:
                if k == "fixed" and limit is None:
                    row[f"{k}_detect"] = row[f"{k}_chance"] = row[f"{k}_net"] = None
                    continue
                m = ed_n if k == "edivisive" else TRIALS
                row[f"{k}_detect"] = round(hits[k] / m, 3)
                row[f"{k}_chance"] = round(chance[k] / m, 3)
                row[f"{k}_net"] = round((hits[k] - chance[k]) / m, 3)
            out["injection"].append(row)
        print(f"{'|'.join(key)} done ({time.time() - t0:.0f}s)", flush=True)

    # 4. scheduled-run reliability (job metadata)
    jobs_path = os.path.join(os.path.dirname(path), "kgateway_nightly_jobs.csv")
    if os.path.exists(jobs_path):
        import csv
        runs, lt, dates = {}, defaultdict(lambda: [0, 0]), set()
        for r in csv.DictReader(open(jobs_path)):
            runs[r["run_id"]] = r["run_conclusion"]
            dates.add(r["date"])
            if r["job_name"].startswith("Load Tests"):
                lt["all"][1] += 1
                lt["all"][0] += r["job_conclusion"] == "success"
        out["reliability"] = dict(first=min(dates), last=max(dates), runs=len(runs), runs_success=sum(v == "success" for v in runs.values()),
                                  loadtest_jobs=lt["all"][1], loadtest_success=lt["all"][0])

    # summary across series per slowdown
    summ = []
    for d in SLOWDOWNS:
        rows = [r for r in out["injection"] if r["slowdown"] == d]
        dl = [r["robust_median_delay"] for r in rows if r["robust_median_delay"] is not None]
        s = dict(slowdown=d, robust_delay=float(np.median(dl)) if dl else None)
        for k in ("robust", "naive", "fixed", "edivisive"):
            for kind in ("detect", "chance", "net"):
                v = [r[f"{k}_{kind}"] for r in rows if r[f"{k}_{kind}"] is not None]
                s[f"{k}_{kind}"] = round(float(np.mean(v)), 3)
        summ.append(s)
    out["injection_summary"] = summ
    json.dump(out, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=str)
    print(json.dumps(dict(backtest=out["backtest_summary"], known=out["known_change"],
                          reliability=out["reliability"], summary=summ), indent=1))
    print(f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else LIVE)
