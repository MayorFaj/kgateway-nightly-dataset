# Analysis for the ICSE 2027 SEIP paper

Scripts behind the industry paper *"The Gate Passed, the Numbers Did Not: Lessons from Nightly Control-Plane Performance Testing of a Kubernetes Gateway API Implementation"* (M. Fajobi).

Requirements: Python 3.10+, numpy, scipy (Fisher's exact test, used only in the paper's text), matplotlib (figures).

| Script | What it does |
| --- | --- |
| `common.py` | Loads `data/nightly/kgateway_nightly_attachedroutes_live.csv` and converts durations to seconds |
| `edivisive.py` | E-divisive change-point detection (Matteson and James, 2014), univariate, alpha 1, permutation test |
| `analyze.py` | Branch summaries, threshold headroom, the 16 nightly series, relative gates, E-divisive and detection delay; writes `results.json` |
| `sensitivity.py` | Relative gates for windows 3/7/14 and k 1.25/1.5/2/3; E-divisive at significance 0.01/0.05 and minimum segment 3/5; noise profile; writes `sensitivity.json` |
| `make_teardown_fig.py` | Nightly 5,000-route teardown per branch (paper Fig. 2) |
| `make_series_fig.py` | The 16 nightly series with change points (paper Fig. 4) |

```bash
cd analysis/seip
python3 analyze.py
python3 sensitivity.py
python3 make_teardown_fig.py ../../data/nightly/kgateway_nightly_attachedroutes_live.csv teardown-nightly.pdf
python3 make_series_fig.py ../../data/nightly/kgateway_nightly_attachedroutes_live.csv series-cpd.pdf
```

CI job metadata (`data/nightly/kgateway_nightly_jobs.csv`) and failed-test classifications (`data/nightly/kgateway_nightly_loadtest_failures.csv`) are produced by `.github/collect_jobs.py` and `.github/failed_tests.py` through the "Collect nightly job metadata" workflow.
