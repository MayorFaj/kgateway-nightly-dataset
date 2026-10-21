# How to run the #14519 A/B experiment

Run it from `MayorFaj/kgateway-nightly-dataset`. The workflow checks out `kgateway-dev/kgateway` itself, so it doesn't need a fork. Actions minutes are free on public repositories.

## 1. Add the files, plan first

1. Commit `experiments/ab-14519/PLAN.md` on its own, with the message "Pre-register #14519 A/B plan". This timestamp is your evidence that the analysis was fixed before you collected any data.
2. Then commit:
   - `.github/workflows/ab-14519.yaml`
   - `experiments/ab-14519/analysis/analyze_ab.py`
   - `experiments/ab-14519/RUN.md`

## 2. Run it

1. In the repo, open **Actions**. If GitHub asks, click "I understand my workflows, go ahead and enable them".
2. Pick **A/B 14519** on the left, then **Run workflow**. Keep the defaults: `max_versions` and `standard`.
3. Eight jobs ("A/B block 1" to "A/B block 8") run in parallel. Expect about 1.5 to 3 hours. Each job builds two sets of images, then runs the 5,000-route test four times.

If a block fails, leave it. The analysis excludes failed trials and reports them. Don't re-run single blocks, because the plan fixes 8 blocks per run.

## 3. Analyse

Either send the eight `ab-14519-block-N` artifacts to Claude, or do it yourself:

```bash
gh run download <run-id> -R MayorFaj/kgateway-nightly-dataset -D results/
pip install numpy scipy matplotlib
python3 experiments/ab-14519/analysis/analyze_ab.py results/
```

This writes `results/report.md` and the figure `ab_teardown.pdf`. The report ends with CONFIRMED, PARTIAL or NOT CONFIRMED, decided by the rule in PLAN.md.

## 4. Afterwards

- Archive the results as a new version of the Zenodo dataset (a new GitHub release, e.g. `v1.1.0`).
- Whatever the outcome, it goes into the workshop paper. If the outcome is CONFIRMED, it also answers the main reviewer question on the ICPE paper.
