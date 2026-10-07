# Defense guide: ab-peeking-audit

What to say about this repository in an interview, with the command that
proves each claim. Every number here is guarded by `tools/check_numbers.py`,
so if this document and the code ever disagree, the build fails.

## The 30 second version

"A final p-value cannot report its own false positive rate, because the
decision procedure that produced it, how many peeks, whether a significant
peek stopped the test, is not in the final counts. I built an auditor that
replays procedures over seeded null experiments: at nominal alpha 0.05, one
pre-registered look runs 5.22%, weekly peeking runs 12.5%, daily peeking
runs 28.15% false positives, with exact intervals. Then it calibrates the
boundary that makes the same schedule honest, verifies it on held-out nulls,
and measures the price: honest daily peeking costs 17.5 points of power
against a single look. The reported p-values across those procedures overlap
completely, which is the point: you cannot audit the report, only the
procedure."

Then stop. The question that usually comes next is "so should teams never
peek", and the answer is no: declare the schedule, calibrate the boundary
for it, accept the measured power price or buy it back with a late-spending
boundary; what is indefensible is peeking at 1.96.

## The claims, each with how it is proved

### 1. The inflation is measured, not asserted

Command: `peek-audit audit --policy daily` (exits 1)

Numbers: daily peeking runs 28.15% false positives, with the exact
interval's floor at 26.76% and ceiling at 29.57%, over 4000 seeded null
experiments; weekly at 12.5%; the single look at 5.22%, CONSISTENT.

If pushed ("these are known results"): yes, Armitage-era, and that is why
measuring them is the right calibration check for the engine; the
repository's contribution is the instrument (exact intervals, verdict
semantics, held-out boundary, the identical-p demonstration), not the
phenomenon.

### 2. The final report carries no bit that distinguishes procedures

Command: `python experiments/exp_identical_pvalue.py`

Numbers: daily-peeked null wins report a median reported p of 0.0347;
single-look false positives a single-look median of 0.0252; the quartile
ranges overlap. And the wins are vapor: of 1126 early wins at a median stop
day of 5, 81.4% of them are no longer significant at the planned horizon.

If pushed ("isn't regression to the mean enough to explain that?"): that is
exactly what it is, named and measured; the early stop freezes a noise
excursion and prevents the regression from being observed, which is why the
procedure, not the snapshot, carries the error rate.

### 3. The honest boundary works and its price is a measurement

Command: `peek-audit boundary --policy daily --seed 11 --holdout-seed 12`
then `python experiments/exp_correction_cost.py`

Numbers: constant z* of 2.731, per-peek alpha of 0.00631, held-out rate of
4.05%. Power at 0.05 vs 0.0575: single look wins 70.8%, naive daily
advertises 83.4% (invalid), corrected daily peeking wins 53.3%; the
correction costs 17.5 points. Context from statsmodels: this effect needs
14178 per arm for 80% at a single look; the horizon here is 11200 subjects
per arm at the horizon.

If pushed ("why is the held-out seed mandatory?"): the bisection lands where
the calibration sample touches alpha, so the in-sample rate equals alpha by
construction and certifies nothing; equal seeds are refused in code.

### 4. The numbers cannot silently go stale

Command: `make verify` (or break a README figure and watch the build fail)

`tools/collect_metrics.py` reads the junit XML, the coverage JSON and the
experiment JSON; nothing is typed by hand. `tools/check_numbers.py` matches
anchor phrases across the README and this document. The suite is 74 tests at
100% line coverage; two of them are pins: one known PRNG draw, and exact
equality between the vectorized z and statsmodels' proportions_ztest.

## Questions that are meant to be hard

**Isn't this just a wrapper around a z-test?** The z-test is one line of the
engine. The instrument is everything the test does not do: the procedure
replay, exact Clopper-Pearson verdicts with an INCONCLUSIVE exit, the
held-out boundary calibration, the counter-based PRNG that keeps every
figure re-measurable across library versions, and the identical-p experiment
that demonstrates the structural gap rather than asserting it.

**Why simulate what Pocock solved in 1977?** ADR-002: the closed forms
assume equal normal increments, which this schedule only approximates; the
simulation prices the approximation, is checked by the same audit it
enforces on others, and the comparison to O'Brien-Fleming is stated as what
the constant boundary leaves on the table, with the scoring harness already
built.

**What is the weakest part?** The constant boundary is the simple valid
correction, not the best one, so the headline 17.5 point cost overstates the
unavoidable price; a late-spending boundary would reclaim part of it, and
the repository says so rather than hiding it. Second weakest: two-proportion
metrics only; continuous metrics change the statistic though not the
argument.

**Your own PRNG? That is usually a red flag.** ADR-001: the alternative is
letting numpy's release notes decide when every published figure changes.
SplitMix64 is twenty lines, counter-based, literature-tested, and one draw
is pinned so a silent change is a red build. The red-flag version is rolling
novel cryptography; this is the opposite: the most boring known-good mixer,
owned for reproducibility.

**What did you get wrong while building it?** The first counter layout made
2000 trials take 82 seconds (the fix, a layout change, is its own commit and
made the sample's definition explicit), and the PRNG pin test failed on its
first run because the expected value had been typed from memory rather than
read from the machine, which is precisely the failure the receipts exist to
catch.

**Does 4000 trials even resolve these claims?** The exact intervals answer
that per claim: the daily interval's floor at 26.76% clears 5% by more than
twenty points, and the holdout floor at 3.46% with the holdout ceiling at
4.71% rules out a doubled alpha. Where the interval cannot rule out
twice alpha, the tool itself says INCONCLUSIVE and exits 2 (ADR-004).

## Things to say and things not to say

Say: "you cannot audit the report, only the procedure", "the early stop
harvests noise and then destroys the evidence", "the in-sample calibrated
rate certifies nothing, the held-out rate is the number", "17.5 points is
the price of the simple correction, not the cheapest honest one".

Do not say: "peeking is forbidden" (declared schedules with calibrated
boundaries are fine; 1.96 at every peek is not). Do not quote 28.15% as a
universal constant (it is this schedule and design; the direction is
universal, the value is not). Do not call the naive 83.4% "power" without
the word invalid attached. Do not claim the PRNG is cryptographic.

## The live demo script

```bash
peek-audit audit --policy single ; echo "exit $?"
peek-audit audit --policy daily ; echo "exit $?"
peek-audit replay --policy daily --seed 42
peek-audit boundary --policy daily --seed 11 --holdout-seed 12
peek-audit samplesize --lift 0.0075
```

The second command's exit 1 is the headline; the replay's closing line,
"this number is all a report keeps", is the thesis in one sentence.
