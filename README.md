# kgateway nightly attached-routes measurements (July to October 2026)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23539157.svg)](https://doi.org/10.5281/zenodo.23539157)

Dataset, collection tool and controlled experiment for kgateway's nightly control-plane scale tests. It accompanies the industry paper *"The Gate Passed, the Numbers Did Not: Lessons from Nightly Control-Plane Performance Testing of a Kubernetes Gateway API Implementation"* (M. Fajobi, under submission).

## Contents

| File | Description |
| --- | --- |
| `kgateway_nightly_attachedroutes_dedup.csv` | 864 measurements, one row per run × branch × Kubernetes version × validation mode × route scale |
| `experiments/ab-14519/` | Pre-registered A/B experiment for PR #14519: plan, workflow run notes, per-trial results, analysis script and report |
| `.github/archive_nightly.py` | Collection tool: parses the nightly job logs into this schema (see *Collection tool*) |
| `.github/verify_dataset.py` | Compares the published CSV with rows re-collected by the tool |
| `.github/workflows/archive-nightly.yaml` | Weekly workflow that archives new nightly runs to `data/nightly/` |
| `.github/workflows/backfill-verify.yaml` | One-off workflow that re-collected all runs whose logs still existed and checked the published rows |
| `data/nightly/kgateway_nightly_attachedroutes_live.csv` | Every nightly run from 24 July 2026 collected by the tool (1,729 rows from 89 runs on 21 October), same columns, growing weekly |
| `data/verification/recollection-report.md` | Result of the re-collection check |
| `data/nightly/kgateway_nightly_jobs.csv` | Conclusion, duration and failed steps of every job of every nightly run from 23 July 2026 (`.github/collect_jobs.py`) |
| `data/nightly/kgateway_nightly_loadtest_failures.csv` | For each failed load-test job: failed Go tests and test-framework error messages (`.github/failed_tests.py`) |
| `analysis/seip/` | Analysis and figure scripts for the ICSE 2027 SEIP paper, including an E-divisive implementation |
| `README.md` | This file |
| `LICENSE-CODE` | Apache License 2.0 for the code |
| `.zenodo.json` | Metadata used by Zenodo when the repository is archived |

## Source

The values come from the public GitHub Actions logs of the nightly workflow (`.github/workflows/nightly-tests.yaml`, scheduled at 05:00 UTC) in [kgateway-dev/kgateway](https://github.com/kgateway-dev/kgateway). The workflow runs the attached-routes load-test suite (`test/e2e/features/loadtesting/attachedroutes_suite.go`) through the composite action `.github/actions/kube-gateway-api-load-tests`.

- **Sampling:** every second scheduled run from 23 July to 21 October 2026, giving 45 runs and 270 load-test jobs (6 per run: 3 branches × 2 Kubernetes versions on kind).
- **Coverage:** the logs of the 23 July run had already expired under GitHub's retention policy (HTTP 410), so the measurements come from the remaining 44 runs, **25 July – 21 October 2026**.
- **Branches:** `main`, `v2.4.x` and `v2.3.x`; `v2.2.x` instead of `v2.4.x` in the runs of 25, 27 and 29 July.
- **Extraction:** each job's log was downloaded and the suite's printed summary block was parsed. The original one-off extraction script was written with the help of an AI assistant; values were spot-checked by hand against the raw logs. The released collection tool re-implements the same parsing and was used to re-collect the published rows (see *Re-collection check*).
- **Deduplication:** some summaries are printed more than once per job. One row was kept per (`run_id`, `branch`, `k8s`, `validation_mode`, `routes`), which reduced 884 parsed rows to 864.

## Columns

| Column | Unit | Meaning |
| --- | --- | --- |
| `date` | YYYY-MM-DD | Date of the scheduled run (UTC) |
| `run_id` | | GitHub Actions workflow run ID |
| `branch` | | `main`, `v2.4.x`, `v2.3.x` or `v2.2.x` (July only) |
| `k8s` | | Kubernetes version label from the CI matrix: `min_versions` (Kubernetes v1.32.5) or `max_versions` (v1.36.1) |
| `job_result` | | Conclusion of the whole CI job: `success` or `failure`. A job can fail because of another suite in the same job |
| `validation_mode` | | `standard` or `strict` on `main` and `v2.4.x`. `?` on `v2.3.x` and `v2.2.x` (188 rows): these older branches run the suite once and their logs do not print a validation mode |
| `routes` | count | Baseline route count: 1000 or 5000 |
| `setup_time` | duration | "Stopwatch" time: from just before creating one extra HTTPRoute until the Gateway's `attachedRoutes` status reaches N+1. Includes the API call that creates the route. Polled every 1 s. The suite's pass/fail limit applies to this value |
| `route_ready_time` | duration | The polling part of `setup_time` only: from the start of status polling until `attachedRoutes` reaches N+1. Always slightly smaller than `setup_time` (by the route-creation call, typically a few milliseconds) |
| `teardown_time` | duration | Time from deleting that route until `attachedRoutes` returns to N. Polled every 100 ms |
| `controller_restart_time` | duration | Time for the controller to recover after a restart (newer branches only). 500 ms steps |
| `post_restart_translation_time` | duration | Time to finish translating the baseline after the restart |
| `status_writes` | count | Number of status writes the suite reported |
| `test_result` | | `PASS` or `FAIL` for this measurement; empty if the job stopped first |

Durations are kept exactly as the Go test printed them, for example `13.037465783s` or `135.423954ms`. Convert them to seconds before analysis.

Empty cells mean the metric was not printed, for example restart metrics on branches without the restart phase, or every metric when the job stopped before the summary. Rows are sorted by date, branch, `k8s`, validation mode and route count.

## Things to know before reusing the data

- **The timings are control-plane latencies seen through status.** They are not data-plane (Envoy) readiness. The suite's log line mentions an HTTP 200 probe, but the code polls Gateway status.
- **Values are quantised by the polling interval:** 1 s for setup, 100 ms for teardown, 500 ms for restart. A setup value of about 1.05 s means "seen at the first poll".
- **Runs used shared GitHub-hosted runners on a single-node kind cluster with simulated Services and EndpointSlices.** Since April 2026 (kgateway PR #13805) the suite no longer creates fake Node objects; of the branches here, only `v2.2.x` still did. Compare values within this dataset, not against production clusters.

## Collection tool

Requirements: Python 3.8+ (standard library only) and the [GitHub CLI](https://cli.github.com/) logged in, or a `GH_TOKEN` environment variable.

```bash
# collect every nightly run newer than the newest row already in the file
python3 .github/archive_nightly.py data/nightly/kgateway_nightly_attachedroutes_live.csv
# backfill: re-read all runs from a date on (logs older than about 90 days are gone)
python3 .github/archive_nightly.py my.csv --since 2026-07-23
# compare the published dataset with re-collected rows
python3 .github/verify_dataset.py kgateway_nightly_attachedroutes_dedup.csv my.csv report.md
```

The weekly workflow `.github/workflows/archive-nightly.yaml` runs the first command every Monday and commits new rows to `data/nightly/`.

## Re-collection check

On 21 October 2026 the backfill workflow re-collected every scheduled nightly run from 24 July 2026 whose logs still existed (89 runs, 1,729 rows, now in `data/nightly/`) and compared the published CSV with the result (`data/verification/recollection-report.md`):

- all 44 published runs were re-collected;
- all 860 published rows that contain metrics are identical in every column;
- the 4 remaining rows are the failed scenarios with no metrics: the job stopped before printing a summary, so the tool emits no row for them.

`data/nightly/` therefore also contains the nights skipped by the every-second-run sampling of the published file.

## Citation

M. Fajobi. 2026. *kgateway nightly attached-routes measurements, July–October 2026.* Dataset. Zenodo. https://doi.org/10.5281/zenodo.23539157

## Licence

Data (CSV files and experiment results): CC BY 4.0. Code (`.py` and workflow files): Apache License 2.0, see `LICENSE-CODE`.
