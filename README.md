![](../../workflows/gds/badge.svg)
![](../../workflows/docs/badge.svg)
![](../../workflows/test/badge.svg)
![](../../workflows/fpga/badge.svg)

# CTW-SPMS

## Programmable Smart Power Management & Supervisor

CTW-SPMS is a 100% digital RTL power-management and supervision ASIC targeting:

- Tiny Tapeout TTSKY26c
- SKY130A
- 1x2 tile
- Top module: tt_um_ctw_spms
- Target clock: 10 MHz

## Frozen architecture

POWER_SAMPLE
-> FIR filter
-> Power deviation
-> Anomaly detector
-> Power-level classifier
-> 4-rail sequencer
-> 3-load priority manager
-> Fault manager
-> Safe outputs

The complete architecture includes:

- FIR power filtering
- absolute power deviation
- persistent anomaly detection
- HIGH / MEDIUM / LOW / CRITICAL classification
- four supervised power rails
- Power-Good synchronization and filtering
- startup timeout
- three prioritized loads
- load shedding
- staged load restoration
- hard-fault shutdown
- fault latch
- watchdog
- automatic retry
- retry lockout
- last-fault register
- fault counter
- SPI Mode 0 configuration/status interface

## ASIC RTL policy

The RTL is developed specifically for SKY130 ASIC implementation:

- deterministic reset behavior
- safe outputs after reset
- no functional initial blocks
- no implicit nets
- explicit arithmetic widths
- explicit signed/unsigned handling
- one primary clock domain
- asynchronous inputs synchronized before control logic
- no generated clocks unless absolutely necessary
- no large general-purpose multipliers or dividers
- synthesis and timing checked incrementally

## Development flow

RTL regression
-> Yosys synthesis
-> LibreLane / OpenROAD
-> STA
-> Gate-level regression
-> Tiny Tapeout precheck
-> GDS

## Current milestone

Milestone 0: CI and safe-state baseline.

The initial RTL deliberately holds all power rails and loads OFF.

After this baseline passes GitHub Actions, functional blocks will be added
incrementally and regression-tested after each major subsystem.

See docs/info.md for additional project documentation.

## License

Apache-2.0 unless otherwise noted.