"""Figure: share of injected slowdowns detected, by method. Reads results.json."""
import json, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "results.json")))
S = D["injection_summary"]
B = D["backtest_summary"]
x = [int(r["slowdown"] * 100) for r in S]
lines = [("History-aware check (proposed)", "robust", "#2a78d6", "o"),
         ("E-divisive change points (retrospective)", "edivisive", "#eb6834", "s"),
         ("One-night relative gate (1.5x)", "naive", "#1baf7a", "^"),
         ("Suite's fixed pass/fail limit", "fixed", "#eda100", "D")]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
fig, (ax, bx) = plt.subplots(1, 2, figsize=(10.5, 4.4), dpi=200, gridspec_kw=dict(width_ratios=[2.1, 1]))
fig.patch.set_facecolor("#fcfcfb")
for a in (ax, bx): a.set_facecolor("#fcfcfb")
seen=set()
for label, key, c, m in lines:
    y = [r[key] * 100 for r in S]
    ax.plot(range(len(x)), y, color=c, lw=2, marker=m, ms=7, mec="#fcfcfb", mew=1.5, label=label)
    if round(y[-1]) in seen: continue
    seen.add(round(y[-1]))
    ax.annotate(f"{y[-1]:.0f}%", (len(x) - 1, y[-1]), xytext=(8, 0), textcoords="offset points",
                va="center", color="#0b0b0b", fontsize=9)
ax.set_xticks(range(len(x)), [f"+{v}%" for v in x])
ax.set_ylim(-3, 105); ax.set_xlim(-0.3, len(x) - 0.4)
ax.set_xlabel("Size of injected persistent slowdown", color="#52514e")
ax.set_ylabel("Slowdowns detected within 10 nights (%)", color="#52514e")
ax.grid(axis="y", color="#e4e3df", lw=0.8); ax.set_axisbelow(True)
for s in ("top", "right"): ax.spines[s].set_visible(False)
for s in ("left", "bottom"): ax.spines[s].set_color("#c3c2b7")
ax.tick_params(colors="#52514e")
ax.legend(frameon=False, loc="upper left", fontsize=8.5)
ax.set_title("A. Injected slowdowns caught (real data, 200 trials per series)", fontsize=10, loc="left", color="#0b0b0b")
names = ["History-aware\ncheck", "One-night\ngate (1.5x)", "Fixed\nlimit"]
vals = [B["robust_alarms"], B["naive_alarms"], B["fixed_alarms"]]
cols = ["#2a78d6", "#1baf7a", "#eda100"]
bars = bx.bar(range(3), vals, color=cols, width=0.6, edgecolor="#fcfcfb", linewidth=2)
for i, v in enumerate(vals):
    bx.annotate(str(v), (i, v), xytext=(0, 4), textcoords="offset points", ha="center", color="#0b0b0b", fontsize=9)
bx.set_xticks(range(3), names, fontsize=8.5)
bx.set_ylabel(f"Alarms on unmodified data ({B['series_nights']} series-nights)", color="#52514e", fontsize=9)
bx.set_title("B. Alarms with no injected slowdown", fontsize=10, loc="left", color="#0b0b0b")
bx.grid(axis="y", color="#e4e3df", lw=0.8); bx.set_axisbelow(True)
for sp in ("top", "right"): bx.spines[sp].set_visible(False)
for sp in ("left", "bottom"): bx.spines[sp].set_color("#c3c2b7")
bx.tick_params(colors="#52514e")
fig.suptitle("kgateway nightly control-plane scale tests, main and v2.4.x, 24 Jul to 2 Nov 2026", fontsize=11, x=0.01, ha="left", color="#0b0b0b")
fig.tight_layout()
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "detection.png")
fig.savefig(out, facecolor=fig.get_facecolor())
print(out)
