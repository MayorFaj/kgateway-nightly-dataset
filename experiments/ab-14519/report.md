# A/B experiment: kgateway PR #14519 and 5,000-route teardown

Run: https://github.com/MayorFaj/kgateway-nightly-dataset/actions/runs/39671050835 (run #2, workflow commit 6cd29d6, 21 October 2026). Kubernetes v1.36.1 (max_versions), validation standard, 8 blocks x 4 trials on GitHub-hosted ubuntu-22.04 runners. Produced by `analyze_ab.py` exactly as committed; see PLAN.md for the pre-registered rule and deviation 1 (run #1 was invalid and is pilot-only). Raw per-trial logs are attached to the run as artifacts.

Trials: 32 run, 32 valid, 0 excluded. Complete blocks (both arms valid): 8.

| Metric | Arm A median (parent) | Arm B median (#14519) | B/A | 95% CI (block bootstrap) | Wilcoxon p (paired blocks) | Mann-Whitney p (one-sided A>B) |
|---|---|---|---|---|---|---|
| teardown_time | 1.331 s (n=16) | 0.182 s (n=16) | 0.14 | 0.10-0.25 | 0.0078 | 2.2e-05 |
| setup_time | 11.039 s (n=16) | 11.038 s (n=16) | 1.00 | 0.92-1.09 | 0.5469 | 0.32 |
| route_ready_time | 11.035 s (n=16) | 11.035 s (n=16) | 1.00 | 0.92-1.09 | 0.6406 | 0.4 |
| controller_restart_time | 4.503 s (n=16) | 4.004 s (n=16) | 0.89 | 0.82-1.40 | 0.4609 | 0.24 |

**Primary outcome:** CONFIRMED: #14519 reduces 5,000-route teardown time by at least 2x (95% CI of B/A 0.10-0.25, paired Wilcoxon p=0.0078).

Per-block teardown medians (s):
- block 1: A 0.783, B 0.185
- block 2: A 2.089, B 0.229
- block 3: A 0.334, B 0.136
- block 4: A 0.681, B 0.135
- block 5: A 0.634, B 0.130
- block 6: A 1.787, B 0.232
- block 7: A 2.234, B 0.183
- block 8: A 1.680, B 0.231
