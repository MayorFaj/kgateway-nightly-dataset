"""Figure 2 of the SEIP paper: nightly 5,000-route teardown per branch, every night 24 Jul - 21 Oct 2026."""
import csv, re, sys, datetime
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def sec(v):
    if not v: return None
    m = re.fullmatch(r"(?:(\d+)m)?([\d.]+)(ms|s|µs)", v)
    return float(m.group(2)) * {"ms": 1e-3, "s": 1, "µs": 1e-6}[m.group(3)] + 60 * int(m.group(1) or 0)

rows = list(csv.DictReader(open(sys.argv[1])))
plt.rcParams.update({"font.size": 7.5, "font.family": "serif", "axes.spines.top": False,
                     "axes.spines.right": False, "pdf.fonttype": 42})
fig, ax = plt.subplots(figsize=(3.45, 2.0))
style = {"main": ("#1f5fa8", "-", "o", "main"), "v2.4.x": ("#c0392b", "--", "s", "v2.4.x"), "v2.3.x": ("#777777", ":", "^", "v2.3.x")}
for b, (c, ls, mk, lab) in style.items():
    d = defaultdict(list)
    for r in rows:
        if r["branch"] == b and r["routes"] == "5000" and r["teardown_time"]:
            d[r["date"]].append(sec(r["teardown_time"]))
    ds = sorted(d)
    x = [datetime.date.fromisoformat(k) for k in ds]
    ax.plot(x, [np.median(d[k]) for k in ds], ls=ls, color=c, lw=0.9, marker=mk, ms=1.8, label=f"{lab} (nightly median)")
# individual v2.4.x measurements above 10 s
hi = [(datetime.date.fromisoformat(r["date"]), sec(r["teardown_time"])) for r in rows
      if r["branch"] == "v2.4.x" and r["routes"] == "5000" and r["teardown_time"] and sec(r["teardown_time"]) > 10]
ax.scatter([h[0] for h in hi], [h[1] for h in hi], marker="x", color="#c0392b", s=12, lw=0.8, zorder=4, label="v2.4.x single runs > 10 s")
ax.axhline(20, color="black", lw=0.6, ls="-.")
ax.text(datetime.date(2026, 9, 27), 22.5, "gate threshold 20 s", fontsize=6.5)
ax.axvline(datetime.date(2026, 8, 12) + datetime.timedelta(hours=21), color="#1f5fa8", lw=0.6, ls=":")
ax.text(datetime.date(2026, 8, 14), 0.105, "#14519 merged", fontsize=6.5, color="#1f5fa8")
ax.set_yscale("log"); ax.set_yticks([0.1, 0.3, 1, 3, 10, 30]); ax.set_yticklabels(["0.1", "0.3", "1", "3", "10", "30"])
ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
ax.set_ylim(0.09, 40); ax.set_ylabel("Teardown, 5,000 routes (s)")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b")); ax.xaxis.set_major_locator(mdates.MonthLocator(bymonthday=1))
ax.grid(axis="y", lw=0.3, color="#dddddd")
ax.legend(frameon=False, fontsize=5.8, loc="upper right", ncol=2, bbox_to_anchor=(1.0, 1.22), handlelength=2.2, columnspacing=0.8)
fig.tight_layout(pad=0.3)
fig.savefig(sys.argv[2]); fig.savefig(sys.argv[2].replace(".pdf", ".png"), dpi=200)
