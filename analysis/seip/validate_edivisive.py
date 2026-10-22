"""Sanity check of edivisive.py on synthetic series with known change points (seeded, reproducible).

Cases, 89 points each (like the nightly series), noise quantised like the CI metrics:
  null      : no change, normal noise                     -> false-positive rate
  step      : mean shift of 2 noise SDs at t=20           -> detection rate, location error
  step_q    : as step, values quantised to 1 noise SD     -> effect of polling quantisation
  spread    : same median, 35% of points from a slow tail before t=20, 2.5% after -> tail change
  two_steps : shifts at t=30 and t=60                     -> multiple change points
"""
import numpy as np, json
from edivisive import e_divisive
rng = np.random.default_rng(14519)
N, REPS = 89, 100

def gen(kind):
    x = rng.normal(0, 1, N)
    if kind in ("step", "step_q"): x[20:] += 2
    if kind == "step_q": x = np.round(x)
    if kind == "spread":
        base = np.full(N, 0.13) + rng.normal(0, 0.005, N)
        p = np.where(np.arange(N) < 20, 0.35, 0.025)
        slow = rng.random(N) < p
        base[slow] += rng.uniform(0.1, 0.4, slow.sum())
        x = base
    if kind == "two_steps": x[30:] += 2; x[60:] -= 2
    return x

truth = {"null": [], "step": [20], "step_q": [20], "spread": [20], "two_steps": [30, 60]}
out = {}
for kind, tcs in truth.items():
    found_all, extra, loc_err = 0, 0, []
    for _ in range(REPS):
        cps = [t for t, p in e_divisive(gen(kind), seed=int(rng.integers(1e9)))]
        hit = [min(cps, key=lambda c: abs(c - t)) for t in tcs if cps and min(abs(c - t) for c in cps) <= 3]
        found_all += len(hit) == len(tcs)
        loc_err += [abs(h - t) for h, t in zip(hit, tcs)]
        extra += max(0, len(cps) - len(hit))
    out[kind] = dict(reps=REPS, all_true_found=found_all, extra_change_points=extra,
                     mean_location_error=round(float(np.mean(loc_err)), 2) if loc_err else None)
    print(kind, out[kind])
json.dump(out, open("validation.json", "w"), indent=1)
