# kgateway nightly attached-routes measurements (July–October 2026)

Dataset accompanying the ICPE 2027 industrial paper *"From One-Off Benchmarks to Nightly Performance Gates: Control-Plane Regression Testing for a Kubernetes Gateway API Implementation"* (M. Fajobi).

## Contents

| File | Description |
| --- | --- |
| `kgateway_nightly_attachedroutes_dedup.csv` | 864 measurements, one row per run × branch × Kubernetes version × validation mode × route scale |
| `README.md` | This file |
| `.zenodo.json` | Metadata used by Zenodo when the repository is archived |

## Source

The values come from the public GitHub Actions logs of the nightly workflow (`.github/workflows/nightly-tests.yaml`, scheduled at 05:00 UTC) in [kgateway-dev/kgateway](https://github.com/kgateway-dev/kgateway). The workflow runs the attached-routes load-test suite (`test/e2e/features/loadtesting/attachedroutes_suite.go`) through the composite action `.github/actions/kube-gateway-api-load-tests`.

- **Sampling:** every second scheduled run from 23 July to 21 October 2026, giving 45 runs and 270 load-test jobs (6 per run: 3 branches × 2 Kubernetes versions on kind).
- **Coverage:** the logs of the 23 July run had already expired under GitHub's retention policy (HTTP 410), so the measurements come from the remaining 44 runs, **25 July – 21 October 2026**.
- **Branches:** `main`, `v2.4.x` and `v2.3.x`; `v2.2.x` instead of `v2.4.x` in the runs of 25, 27 and 29 July.
- **Extraction:** each job's log was downloaded and the suite's printed summary block was parsed. The extraction script was written with the help of an AI assistant; values were checked by hand against the raw logs.
- **Deduplication:** some summaries are printed more than once per job. One row was kept per (`run_id`, `branch`, `k8s`, `validation_mode`, `routes`), which reduced 884 parsed rows to 864.

## Columns

| Column | Unit | Meaning |
| --- | --- | --- |
| `date` | YYYY-MM-DD | Date of the scheduled run (UTC) |
| `run_id` | — | GitHub Actions workflow run ID |
| `branch` | — | `main`, `v2.4.x`, `v2.3.x` or `v2.2.x` (July only) |
| `k8s` | — | Kubernetes version label from the CI matrix: `min_versions` (Kubernetes v1.32.5) or `max_versions` (v1.36.1) |
| `job_result` | — | Conclusion of the whole CI job: `success` or `failure`. A job can fail because of another suite in the same job |
| `validation_mode` | — | `standard` or `strict` (strict only on `main` and `v2.4.x`) |
| `routes` | count | Baseline route count: 1000 or 5000 |
| `setup_time` | duration | "Stopwatch" time: from just before creating one extra HTTPRoute until the Gateway's `attachedRoutes` status reaches N+1. Includes the API call that creates the route. Polled every 1 s. The suite's pass/fail limit applies to this value |
| `route_ready_time` | duration | The polling part of `setup_time` only: from the start of status polling until `attachedRoutes` reaches N+1. Always slightly smaller than `setup_time` (by the route-creation call, typically a few milliseconds) |
| `teardown_time` | duration | Time from deleting that route until `attachedRoutes` returns to N. Polled every 100 ms |
| `controller_restart_time` | duration | Time for the controller to recover after a restart (newer branches only). 500 ms steps |
| `post_restart_translation_time` | duration | Time to finish translating the baseline after the restart |
| `status_writes` | count | Number of status writes the suite reported |
| `test_result` | — | `PASS` or `FAIL` for this measurement; empty if the job stopped first |

Durations are kept exactly as the Go test printed them, for example `13.037465783s` or `135.423954ms`. Convert them to seconds before analysis.

Empty cells mean the metric was not printed, for example restart metrics on branches without the restart phase, or every metric when the job stopped before the summary. Rows are sorted by date, branch, `k8s`, validation mode and route count.

## Things to know before reusing the data

- **The timings are control-plane latencies seen through status.** They are not data-plane (Envoy) readiness. The suite's log line mentions an HTTP 200 probe, but the code polls Gateway status.
- **Values are quantised by the polling interval:** 1 s for setup, 100 ms for teardown, 500 ms for restart. A setup value of about 1.05 s means "seen at the first poll".
- **Runs used shared GitHub-hosted runners on a single-node kind cluster with simulated nodes, Services and EndpointSlices.** Compare values within this dataset, not against production clusters.

## Citation

M. Fajobi. 2026. *kgateway nightly attached-routes measurements, July–October 2026.* Dataset. Zenodo. DOI: [add after archiving]

## Licence

CC BY 4.0
