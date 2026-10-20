# Shared model and experimental methodology

[Project overview](../README.md)

## Physical and controller scope

The Python implementation follows the supplied rotational attitude and motor
dynamics. Roll and pitch regulate angle using outer proportional loops and
inner discrete controller sections. Yaw regulates angular rate, not heading;
its derivative gain is fixed to zero. Eight adjustable gains are bounded as follows.

| Parameter | Lower bound | Upper bound | Search scale |
| --- | --- | --- | --- |
| roll_outer_K | 1.0 | 30.0 | log |
| roll_inner_Kp_equivalent | 0.005 | 0.35 | log |
| roll_inner_Ki_equivalent | 0.0001 | 1.5 | log |
| pitch_outer_K | 1.0 | 30.0 | log |
| pitch_inner_Kp_equivalent | 0.005 | 0.35 | log |
| pitch_inner_Ki_equivalent | 0.0001 | 1.5 | log |
| yaw_Kp | 0.01 | 1.0 | log |
| yaw_Ki | 0.0001 | 0.5 | log |

For normalized coordinate u in [0,1], `gain = exp(log(lower) + u*log(upper/lower))`.
The original controller is included in initialization. Optimized gains from
previous methods are not injected into the main comparison runs.

Motor dynamics retain `tau*d(omega)/dt + omega = 1148*command - 141.4`.
Negative motor speeds can arise at low commands and are penalized as infeasible;
the plant equation is not silently clipped to hide them. Rotational drag is
quadratic in angular rate. The controller step is assumed to be 1 ms and mixer
step 4 ms; the nominal integration step is 1 ms. Roll/pitch export the discrete
pole 0.9997 with exact numerator coefficients. Equivalent Kp/Ki labels are not
instructions to replace the block with an arbitrary ideal PI controller.

## Training objective

For each commanded channel with response horizon T, the speed score is:

```text
0.45 * settling_time/T
+ 0.20 * rise_time/T
+ 0.25 * 2*normalized_ITAE/T^2
+ 0.10 * normalized_IAE/T
```

Scores are averaged over commanded channels for each scenario. The quality
aggregate is `Q = 0.7*mean(speed) + 0.3*max(speed) + 0.01*mean(effort)`.
If summed constraint violation V is at most 1e-10, fitness is Q; otherwise it is
`1000 + 100*V + (2/pi)*atan(Q)`. Penalty values must not be interpreted as seconds
or percentage tracking improvements. Lower fitness is better for the same cases.

Overshoot is normalized by command amplitude; rise time uses the 10–90% crossings.
Settling uses a 2% band and the final hold requirement. The configuration limits
overshoot to 10%, final error to 2%, and motor clipping to 5%. Additional penalties
cover unsettled responses, uncommanded cross-axis motion, excessive angle,
negative motor speed, divergence, and nonfinite values. See `assess()` and
`evaluate()` in the study source for exact calculation.

## Experiment groups must remain separate

| Group | Training and budget | Interpretation |
| --- | --- | --- |
| Original single-method studies | Three seeds (11,29,47), usually 64 candidates and 50 updates | Method behavior and sensitivity; equal iterations do not mean equal evaluation cost |
| Five-method nominal benchmark | 30 seeds, 3,264 unique evaluations per run, six nominal commands | Paired comparison under one common training objective |
| Five-method robust benchmark | Same 30 seeds and budget, 30 training scenarios | Separate uncertainty-focused tuning |
| Six-method extension | Four development settings, then 30 main seeds per regime and 3,264 evaluations | Equal final budget, additional development effort versus original five |

The 30 seeds are 11, 29, 47, and every integer from 101 to 127. Shared stratified
64-point initial populations and the source baseline consume the budget. Cache
keys use coordinates rounded to 13 decimal places. Duplicates do not consume
additional evaluations. The final partial batch is cut at the remaining budget,
and all evaluated points participate in the best archive. There is no padding.
GA mutation and PSO inertia schedules in the benchmark depend on budget progress.

Nominal training commands are roll 5/20 degrees, pitch 5/20 degrees, and yaw rate
30/100 degrees per second. The later robust training adds three single-axis
commands on each of eight uncertain plants: six Latin-hypercube draws plus two
directed boundary plants. This makes 30 training cases. The original three-seed
studies use their own smaller robust-training and Monte Carlo protocols; do not
confuse them with the later 30-seed protocol.

## Uncertainty and held-out validation

| Factor | Relative range |
| --- | --- |
| Jxx, Jyy, Jzz | ±15% independently |
| Motor time constant | ±30% |
| Thrust coefficient Ct | ±10% |
| Reaction torque coefficient Cm | ±10% |
| Quadratic damping on each axis | ±30% independently |

These are assumed ranges, not measured manufacturing tolerances. Later held-out
validation uses 300 random single-axis cases, 54 one-factor boundary cases, and
90 separate combined-axis stress cases. Best/median representatives additionally
receive 1,536 joint-boundary checks. Physically admissible inertia subsets are
reported separately. Fixed validation cases are reused across methods, so pooled
pass counts are descriptive, not independent estimates of flight reliability.

The six extension methods test four settings on development seeds 5011, 5021,
and 5039 under both training regimes: 24 development runs per method, 144 total.
Selection uses average within-seed, within-regime ranks; ties choose the earlier
candidate. Each selected setting is then frozen for both regimes and 60 main runs.

## Statistics and interpretation

Primary descriptive comparisons use median constrained fitness over 30 seeds.
Mean, sample standard deviation, quartiles, extrema, feasible-run counts, and
bootstrap intervals are retained. Friedman comparisons use within-seed
permutation tests (20,000 draws). Paired Wilcoxon comparisons use Holm correction;
their null assumes symmetric paired differences. Bootstrap intervals use 10,000
resamples and are not multiplicity-adjusted. Each scope/regime has its own family.

The best representative is selected by training fitness. The median representative
is the actual run closest to the median, with seed as tie-breaker. Validation is
not used to choose them. Thirty seeds measure optimizer randomness on one model;
they are not thirty independent control problems. See each `statistics.json`
and paired-comparison CSV for details and numerical settings.

Finite simulations do not establish continuous-range robustness, compiled
Simulink equivalence, global optimality, or suitability for hardware deployment.
Combined-axis failures and infeasible runs are part of the results.
