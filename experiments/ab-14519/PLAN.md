# Pre-registered plan: controlled A/B test of kgateway PR #14519

Written 21 October 2026, before any A/B data was collected. Commit this file to the repository before running the experiment, so its timestamp shows the plan came first.

## 1. Question

The nightly data (Zenodo DOI 10.5281/zenodo.23539157) shows 5,000-route teardown time on `main` dropping from a median of 1.85 s to 0.25 s between the 12 and 14 August 2026 runs. PR #14519 ("Scale KRT status writes with keyed contributions", merged 12 August 2026, 20:59 UTC) is the only performance-related change in that window. **Does #14519 cause the drop?**

## 2. Hypotheses

- **H1 (primary):** median teardown time at 5,000 routes is at least 2x lower with #14519 than without it.
- **H0:** no difference.
- **Secondary, exploratory:** #14519 does not change setup (status-observed) time. The nightly data shows no change in setup time at the merge.

## 3. Arms

| Arm | Commit | Description |
|---|---|---|
| A | `12a81d42cba2b018922ab857c5abf4b214053515` | parent of #14519 |
| B | `cf20dc590c3b920a926974848bd6fd4b05907561` | #14519 merge commit |

Verified before the experiment: `git diff A B -- test/e2e/features/loadtesting` is empty, and the Helm charts, `hack/`, `Makefile` and `.github/` are identical between A and B. Only product code differs, mainly `pkg/kgateway/proxy_syncer` (the status-syncing path).

## 4. Procedure

- Runner: GitHub-hosted `ubuntu-22.04`, the same runner image as the nightly job.
- Cluster: single-node kind; Kubernetes v1.36.1 (`max_versions.env`); validation `standard`.
- Test: `make run-load-tests-production`, the attached-routes suite at 5,000 routes. Its code is identical in both arms.
- **Blocks:** 8 independent jobs. Each job builds both arms' images (tags `ab-a`, `ab-b`), creates one kind cluster and runs 4 trials.
- **Counterbalancing:** even blocks run A B B A and odd blocks run B A A B, which cancels warm-up and order effects.
- Between trials, kgateway is uninstalled and reinstalled with the other arm's image. The CRDs and the cluster stay in place.
- The image tag of every trial is recorded and checked.

Total: 32 trials, 16 per arm.

## 5. Measurements

The suite's own summary lines, recorded per trial:
- `Teardown Time` (primary; polled every 100 ms);
- `Setup Time (Stopwatch)`;
- `Route Ready Time`;
- `Controller Restart Time`;
- `Post-Restart Translation Check Time`;
- `Total Writes`.

## 6. Analysis (fixed in advance; implemented in `analysis/analyze_ab.py`)

- **Exclusions:** a trial is excluded if `go test` exits non-zero, if teardown is missing, or if the running image tag does not match the arm. Every exclusion is reported. A block counts only if both arms have at least one valid trial.
- **Effect size:** median(B) / median(A) of teardown, with a 95% percentile-bootstrap CI that resamples whole blocks (10,000 resamples, seed 14519).
- **Paired test:** Wilcoxon signed-rank test on the per-block log of mean(B) / mean(A). There are 8 pairs; the smallest attainable two-sided p is 0.0078.
- **Decision rule:**
  - **CONFIRMED** if Wilcoxon p < 0.05 **and** the upper CI bound of B/A < 0.5.
  - **PARTIAL** if p < 0.05 and the CI lies below 1 but not below 0.5.
  - **NOT CONFIRMED** otherwise.
- **Operating characteristics** (simulated with 300 runs per case, 2 trials per arm per block, noise at 35% of the mean as in the nightly data):

  | True effect | Outcome |
  |---|---|
  | None | CONFIRMED 0%, PARTIAL 3%, NOT CONFIRMED 97% |
  | Nightly-sized (1.85 s to 0.25 s) | CONFIRMED 100% |
  | Smaller (1.85 s to 1.2 s) | PARTIAL 62% |

- **Secondary:** the same summaries for setup and route-ready time, reported descriptively without a decision rule.

## 7. Reporting

All trials are reported whatever the outcome, including a NOT CONFIRMED result. The raw CSVs, logs and environment files are archived next to the existing dataset as a new Zenodo version.

## 8. Deviations

Any change to this plan after data collection starts is listed here with its reason.

- (none yet)
