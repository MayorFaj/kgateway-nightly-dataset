"""Figure: the 16 nightly series (median per night) with E-divisive change points (sig 0.05, min segment 3)."""
import csv, re, sys, datetime
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from edivisive import e_divisive

def sec(v):
    if not v: return None
    m = re.fullmatch(r"(?:(\d+)m)?([\d.]+)(ms|s|µs)", v)
    return float(m.group(2)) * {"ms": 1e-3, "s": 1, "µs": 1e-6}[m.group(3)] + 60 * int(m.group(1) or 0)

rows = list(csv.DictReader(open(sys.argv[1])))
plt.rcParams.update({"font.size": 6.5, "font.family": "serif", "axes.spines.top": False,
                     "axes.spines.right": False, "pdf.fonttype": 42})
metrics = [("setup_time", "setup"), ("teardown_time", "teardown"), ("controller_restart_time", "restart")]
branches = [("main", "#1f5fa8"), ("v2.4.x", "#c0392b"), ("v2.3.x", "#666666")]
cols = [(b, c, sc) for (b, c) in branches for sc in ("1000", "5000")]
fig, axes = plt.subplots(3, 6, figsize=(7.16, 3.3), sharex=True)
for i, (m, ml) in enumerate(metrics):
    for j, (b, c, sc) in enumerate(cols):
        ax = axes[i, j]
        if m == "controller_restart_time" and b == "v2.3.x":
            ax.axis("off"); ax.text(0.5, 0.5, "no restart phase", ha="center", va="center", fontsize=6, color="#888888", transform=ax.transAxes); continue
        d = defaultdict(list)
        for r in rows:
            if r["branch"] == b and r["routes"] == sc and r[m]:
                d[r["date"]].append(sec(r[m]))
        ds = sorted(d); y = np.array([np.median(d[k]) for k in ds]); x = [datetime.date.fromisoformat(k) for k in ds]
        ax.plot(x, y, color=c, lw=0.6)
        for t, p in e_divisive(y):
            ax.axvline(x[t], color="black", lw=0.8, ls="--")
        if i == 0: ax.set_title(f"{b}, {int(sc):,} routes", fontsize=6.3, pad=2)
        if j == 0: ax.set_ylabel(f"{ml} (s)", fontsize=6.5)
        ax.tick_params(labelsize=5.3, length=2, pad=1)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b")); ax.xaxis.set_major_locator(mdates.MonthLocator())
        lo, hi = y.min(), y.max(); pad = (hi - lo) * 0.12 + 1e-3; ax.set_ylim(max(0, lo - pad), hi + pad)
fig.tight_layout(pad=0.2, h_pad=0.3, w_pad=0.3)
fig.savefig(sys.argv[2]); fig.savefig(sys.argv[2].replace(".pdf", ".png"), dpi=200)
