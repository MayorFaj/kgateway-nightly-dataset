"""Figure 2: per-runner teardown in the #14519 A/B experiment (run 39671050835)."""
import csv, glob, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sec = lambda v: float(v[:-2]) / 1000 if v.endswith("ms") else float(v[:-1])
rows = [r for f in sorted(glob.glob(sys.argv[1] + "/**/results-block-*.csv", recursive=True)) for r in csv.DictReader(open(f))]
plt.rcParams.update({"font.size": 8, "font.family": "serif", "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
fig, ax = plt.subplots(figsize=(3.33, 1.75))
style = {"a": dict(color="#555555", marker="o", s=14, label="parent (A)", dx=-0.13),
         "b": dict(color="#1f5fa8", marker="o", s=14, label="#14519 (B)", dx=0.13)}
for arm in ("a", "b"):
    st = dict(style[arm]); dx = st.pop("dx")
    pts = [(int(r["block"]) + dx, sec(r["teardown_time"])) for r in rows if r["arm"] == arm and r["exit_code"] == "0"]
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], zorder=3, linewidths=0, **st)
ax.set_xticks(range(1, 9)); ax.set_xlabel("Runner (block)"); ax.set_ylabel("Teardown (s)")
ax.set_ylim(0, 2.5); ax.grid(axis="y", lw=0.3, color="#dddddd")
ax.legend(frameon=False, fontsize=6.5, loc="upper left", ncol=2, bbox_to_anchor=(0.0, 1.13), handletextpad=0.2, columnspacing=1.0)
fig.tight_layout(pad=0.3)
fig.savefig(sys.argv[2]); fig.savefig(sys.argv[2].replace(".pdf", ".png"), dpi=200)
print(len(rows))
