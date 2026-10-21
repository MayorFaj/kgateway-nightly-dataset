#!/usr/bin/env python3
"""Analyse the #14519 A/B experiment exactly as pre-registered in PLAN.md.

Usage:
    gh run download <run-id> -R <you>/kgateway -D results/
    python3 analyze_ab.py results/            # writes report.md and ab_teardown.pdf/png

Input: every results-block-*.csv found under the given directory.
"""
import csv, glob, math, os, re, sys
import numpy as np
from scipy import stats

SEED = 14519
N_BOOT = 10000


def seconds(v):
    """Parse a Go duration string ('254.1ms', '12.05s', '1m3.2s', '850µs') to seconds."""
    if v is None or v.strip() == "":
        return None
    v = v.strip()
    total, matched = 0.0, False
    for num, unit in re.findall(r"([0-9.]+)(h|ms|µs|us|ns|m|s)", v):
        matched = True
        total += float(num) * {"h": 3600, "m": 60, "s": 1, "ms": 1e-3, "µs": 1e-6, "us": 1e-6, "ns": 1e-9}[unit]
    return total if matched else None


def load(root):
    rows = []
    for path in sorted(glob.glob(os.path.join(root, "**", "results-block-*.csv"), recursive=True)):
        with open(path, newline="") as f:
            rows.extend(csv.DictReader(f))
    return rows


def boot_ratio_ci(blocks, metric, rng):
    """Bootstrap (resampling whole blocks) 95% CI for median(B)/median(A)."""
    keys = list(blocks)
    ratios = []
    for _ in range(N_BOOT):
        pick = rng.choice(keys, size=len(keys), replace=True)
        a = [x for k in pick for x in blocks[k]["a"][metric]]
        b = [x for k in pick for x in blocks[k]["b"][metric]]
        if a and b:
            ratios.append(np.median(b) / np.median(a))
    return np.percentile(ratios, [2.5, 97.5])


def decide(lo, hi, p_w, alpha=0.05):
    """Pre-registered decision rule (PLAN.md, section 6)."""
    if not (p_w < alpha) or lo <= 1.0 <= hi or lo > 1.0:
        return ("NOT CONFIRMED: the paired Wilcoxon test is not significant at 0.05 and/or the 95% CI of B/A "
                "includes 1; #14519 is not shown to cause the improvement.")
    if hi < 0.5:
        return ("CONFIRMED: #14519 reduces 5,000-route teardown time by at least 2x "
                f"(95% CI of B/A {lo:.2f}-{hi:.2f}, paired Wilcoxon p={p_w:.4f}).")
    return (f"PARTIAL: #14519 makes teardown faster (95% CI of B/A {lo:.2f}-{hi:.2f}, p={p_w:.4f}) "
            "but by less than the pre-registered 2x threshold.")


def main(root):
    rows = load(root)
    if not rows:
        sys.exit(f"no results-block-*.csv files under {root}")
    metrics = ["teardown_time", "setup_time", "route_ready_time", "controller_restart_time"]
    valid, excluded = [], []
    for r in rows:
        r["_t"] = {m: seconds(r.get(m)) for m in metrics}
        ok = r.get("exit_code") == "0" and r["_t"]["teardown_time"] is not None
        expected_tag = f":ab-{r['arm']}"
        if not r.get("image", "").endswith(expected_tag):
            ok = False
            r["_why"] = f"wrong image {r.get('image')}"
        elif not ok:
            r["_why"] = f"exit_code={r.get('exit_code')} or missing teardown"
        (valid if ok else excluded).append(r)

    blocks = {}
    for r in valid:
        b = blocks.setdefault(r["block"], {"a": {m: [] for m in metrics}, "b": {m: [] for m in metrics}})
        for m in metrics:
            if r["_t"][m] is not None:
                b[r["arm"]][m].append(r["_t"][m])
    complete = {k: v for k, v in blocks.items() if v["a"]["teardown_time"] and v["b"]["teardown_time"]}

    rng = np.random.default_rng(SEED)
    out = ["# A/B experiment: kgateway PR #14519 and 5,000-route teardown", ""]
    out.append(f"Trials: {len(rows)} run, {len(valid)} valid, {len(excluded)} excluded. Complete blocks (both arms valid): {len(complete)}.")
    for r in excluded:
        out.append(f"- excluded block {r['block']} trial {r['trial']} arm {r['arm']}: {r.get('_why')}")
    out.append("")
    out.append("| Metric | Arm A median (parent) | Arm B median (#14519) | B/A | 95% CI (block bootstrap) | Wilcoxon p (paired blocks) | Mann-Whitney p (one-sided A>B) |")
    out.append("|---|---|---|---|---|---|---|")
    verdict = None
    for m in metrics:
        a = [x for k in complete for x in complete[k]["a"][m]]
        b = [x for k in complete for x in complete[k]["b"][m]]
        if not a or not b:
            continue
        ratio = np.median(b) / np.median(a)
        lo, hi = boot_ratio_ci(complete, m, rng)
        pairs = [(np.mean(complete[k]["a"][m]), np.mean(complete[k]["b"][m])) for k in complete
                 if complete[k]["a"][m] and complete[k]["b"][m]]
        diffs = [math.log(bb) - math.log(aa) for aa, bb in pairs if aa > 0 and bb > 0]
        p_w = stats.wilcoxon(diffs).pvalue if len(diffs) >= 5 and any(d != 0 for d in diffs) else float("nan")
        p_mw = stats.mannwhitneyu(a, b, alternative="greater").pvalue
        out.append(f"| {m} | {np.median(a):.3f} s (n={len(a)}) | {np.median(b):.3f} s (n={len(b)}) | {ratio:.2f} | {lo:.2f}-{hi:.2f} | {p_w:.4f} | {p_mw:.2g} |")
        if m == "teardown_time":
            verdict = decide(lo, hi, p_w)
    out += ["", f"**Primary outcome:** {verdict}", ""]
    out.append("Per-block teardown medians (s):")
    for k in sorted(complete, key=int):
        out.append(f"- block {k}: A {np.median(complete[k]['a']['teardown_time']):.3f}, B {np.median(complete[k]['b']['teardown_time']):.3f}")
    with open(os.path.join(root, "report.md"), "w") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams.update({"font.size": 8, "font.family": "serif", "pdf.fonttype": 42})
        fig, ax = plt.subplots(figsize=(3.33, 1.9))
        ks = sorted(complete, key=int)
        for i, k in enumerate(ks):
            for arm, col, dx in (("a", "#555555", -0.12), ("b", "#1f5fa8", 0.12)):
                ys = complete[k][arm]["teardown_time"]
                ax.scatter([i + 1 + dx] * len(ys), ys, s=10, color=col, label={"a": "parent", "b": "#14519"}[arm] if i == 0 else None)
        ax.set_xticks(range(1, len(ks) + 1)); ax.set_xlabel("Block (one runner each)")
        ax.set_ylabel("Teardown (s)"); ax.set_ylim(bottom=0)
        ax.legend(frameon=False, fontsize=6.5); ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout(pad=0.3)
        fig.savefig(os.path.join(root, "ab_teardown.pdf")); fig.savefig(os.path.join(root, "ab_teardown.png"), dpi=200)
    except Exception as e:  # plotting is optional
        print("plot skipped:", e)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
