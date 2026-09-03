# CTW-SPMS tapeout signoff record

## Decision

**PASS WITH BOUNDED MAX-SLEW WAIVER** for the frozen TTSKY26c release scope.

The waiver is intentionally narrow and measurable. It does not change the
0.750 ns signoff transition constraint, suppress report rows, add a false path,
or claim that the electrical report is violation-free. It is a CTW-SPMS release
criterion, not a foundry or Tiny Tapeout rule.

## Release policy

The candidate is blocked unless all of the following remain true:

| Gate | Requirement |
|---|---|
| RTL regression | PASS |
| Gate-level regression | PASS |
| Tiny Tapeout precheck | PASS |
| Routing and Magic DRC | 0 final violations |
| LVS | unique match; 0 errors/differences |
| Antenna | 0 violating nets and pins |
| Setup and hold | 0 violations and TNS = 0 at every reported corner |
| Max capacitance | 0 violations |
| Max fanout | 0 violations |
| Max slew | target 0; bounded waiver below may be used |

The max-slew waiver is valid only when every condition below holds:

1. at most two reported pins are affected;
2. worst transition overshoot is no more than 5.0% over the library limit;
3. the reported pins belong to one reviewed, fanout-one synchronous data net;
4. the net is not clock, reset, asynchronous control, or a final safety output;
5. setup, hold, capacitance, and fanout remain clean at every signoff corner;
6. RTL, gate-level, precheck, DRC, LVS, and antenna gates pass.

`scripts/check_signoff.py` enforces the numeric hard gates and the slew bounds
in GDS CI. The semantic single-data-net mapping is reviewed and recorded below.
Any RTL, synthesis, PDK, standard-cell, constraint, or PnR-flow change requires
a fresh review; this waiver must not be carried forward automatically.

## Audited baseline

Evidence is from commit
[`f9a0289abd6d0f9764383dade6bb687c73afc16c`](https://github.com/rakuichijo2001-sketch/ttsky26c-ctw-spms/commit/f9a0289abd6d0f9764383dade6bb687c73afc16c)
and GDS workflow
[`33744014852`](https://github.com/rakuichijo2001-sketch/ttsky26c-ctw-spms/actions/runs/33744014852).
The downloaded `GDS_logs` artifact ID was `9889142743`; its ZIP SHA-256 was
`a2273abdf0be92a598c5952d20f1ca52b7c85faba959b97d838ad8e5fc4ead84`.

The final post-route netlist maps both report rows to net `_0339_`:

- driver `_2967_/Y`: `sky130_fd_sc_hd__nor2_2`;
- only load `_3337_/D`: `sky130_fd_sc_hd__dfrtp_2`;
- sequential destination: `u_spi_slave.bit_count[1]`;
- fanout: 1.

This is SPI counter next-state data. It is not a clock, reset, asynchronous
control, rail/load enable, fault shutdown, or top-level output path.

### Max-slew evidence

| RC/PVT corner | Driver `_2967_/Y` | Load `_3337_/D` | Limit | Result |
|---|---:|---:|---:|---|
| `nom_ss_100C_1v60` | 0.750684 ns | 0.750696 ns | 0.750000 ns | +0.0928% worst |
| `max_ss_100C_1v60` | 0.784516 ns | 0.784557 ns | 0.750000 ns | +4.6076% worst |
| Other seven reported corners | clean | clean | 0.750000 ns | 0 violations |

The two report rows are the two ends of the same fanout-one net, not two
independent problem nets. The full worst case is the `max_ss` value above; the
smaller nominal-RC excess alone is not used to justify the waiver.

### Hard-gate evidence

| Check | Audited result |
|---|---:|
| Setup violations / TNS | 0 / 0.0000 ns |
| Worst setup slack | +71.7912 ns |
| Hold violations / TNS | 0 / 0.0000 ns |
| Worst hold slack | +0.0593 ns |
| Max capacitance violations | 0 |
| Max fanout violations | 0 |
| Final routed DRC | 0 |
| Magic DRC | 0 |
| LVS errors/differences | 0; circuits match uniquely |
| Antenna violating nets / pins | 0 / 0 |
| RTL test / docs / GDS / viewer / precheck / GL jobs | PASS |

Post-route extraction reported 27 unannotated drivers and zero partially
unannotated drivers. Inspection identifies them as unused top-level inputs,
clock-load helper outputs, and constant HI/LO sources; no functional internal
data driver is partially annotated.

## Physical-iteration decision

The accepted candidate is the best measured configuration in the completed
physical experiment set. Representative regressions were:

| Candidate | Max slew | Max fanout | Outcome |
|---|---:|---:|---|
| `f9a0289` (`DESIGN_REPAIR_MAX_SLEW_PCT=50`) | 2 | 0 | accepted bounded result |
| `ae5db27` (`DESIGN_REPAIR_MAX_SLEW_PCT=55`) | 6 | 1 | worse |
| `090d5b9` physical experiment | 8 | 3 | worse |
| `f2691b7` four-bit SPI counter experiment | 28 | 4 | worse |

Further unproven tightening is not a release requirement. It risks moving or
multiplying routed violations for no functional or timing benefit. The
five-percent CI ceiling still rejects any meaningful regression.

## Frozen-scope audit

| Area | Audited result |
|---|---|
| Target | SKY130A, Tiny Tapeout TTSKY26c, 1x2 tile, 10 MHz |
| Clocking | one RTL clock; timers use a clock-enable tick; SPI SCLK is synchronized data |
| CDC | two-flip-flop synchronization on asynchronous PG, fault, watchdog, force, `ena`, and SPI inputs |
| Signal path | four-tap multiplier-free FIR, unsigned deviation, sample-strobed anomaly persistence |
| Rails | ordered startup, qualified PG, per-rail timeout, RUN PG-loss, reverse shutdown |
| Loads | HIGH/MEDIUM/LOW/CRITICAL policy, prompt shedding, staged restoration |
| Safety | deterministic fault priority, combinational final shutdown override, latch/retry/lock/watchdog |
| SPI/registers | Mode 0 framing, atomic writes, documented defaults/status map |
| Reset/state | safe active-low reset; illegal rail encoding recovers OFF; all four fault-controller encodings are defined |
| Documentation | README, `info.yaml`, pin map, register map, RTL, and regression agree |
| Excluded scope | no UART, I2C, PMBus, PWM, analog ADC, CPU, AI/BNN, or BIST |

## Freeze rule

After the release commit passes all CI jobs, merge it to `main`, verify the
same hard gates on the merged commit, and tag that exact commit. Changes after
the tag require a new candidate, full regression, and a new signoff record.
