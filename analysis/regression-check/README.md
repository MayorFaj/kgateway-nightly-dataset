# History-aware regression check for kgateway's nightly scale tests

This folder tests whether comparing each nightly run with the nights before it catches performance regressions in kgateway's control-plane scale tests, and how it compares with the methods in use or proposed so far. Everything runs on the public nightly data in this repository (`data/nightly/kgateway_nightly_attachedroutes_live.csv`, 24 July to 2 November 2026).

## The check

For each branch, metric and route scale, the check takes each night's median and compares it with the median of the previous **14** nights. A night is "bad" when it is more than **3** robust deviations (1.4826 × median absolute deviation, never less than a quarter of the polling interval) above that baseline **and** at least **5%** worse. An alarm is raised after **2** bad nights in a row. These four values were fixed before any results were computed and were not tuned.

## How it was tested

1. **Backtest.** The check was run over the real, unmodified series: main and v2.4.x × setup, teardown and controller-restart time × 1,000 and 5,000 routes (12 series, 978 series-nights after the 14-night warm-up). Any alarm here is a candidate regression to be checked against the branch's commits.
2. **Known real change.** kgateway PR #14519 cut main's 5,000-route teardown from a median of 1.81 s to 0.25 s on 13 August 2026 (confirmed by the controlled A/B experiment in `experiments/ab-14519/`). The same check, run in the "faster" direction, measures how quickly it notices this change.
3. **Injected slowdowns.** Persistent slowdowns of 5%, 10%, 20%, 50% and 100% were added to the real data from a random night onwards, 200 trials per series and size. Each slowed value is re-observed on the suite's polling grid (1 s setup, 100 ms teardown, 500 ms restart), so the simulation respects the measurement resolution. A slowdown counts as caught if an alarm is raised within 10 nights.
4. **Comparisons.** The same trials were scored for the suite's fixed pass/fail limits (setup 30 s / 90 s, teardown 10 s / 20 s; the suite has no limit for restart time), a one-night relative gate (night > 1.5 × median of the previous 7), and E-divisive change-point detection (`analysis/seip/edivisive.py`, 40 trials per series and size). E-divisive is retrospective: it looks at the whole series, including nights after the change, so it is an upper bound rather than a nightly gate.

## Files

| File | What it does |
| --- | --- |
| `regression_check.py` | The check, the backtest, the injection study and the comparisons; writes `results.json` |
| `make_fig.py` | Draws `detection.png` from `results.json` |
| `results.md` | Results and interpretation |

```bash
cd analysis/regression-check
python3 regression_check.py        # about 9 minutes; fixed random seed
python3 make_fig.py
```

Requirements: Python 3.10+, numpy, matplotlib. Code: Apache License 2.0.
