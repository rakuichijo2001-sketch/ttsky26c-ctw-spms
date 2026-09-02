# CTW-SPMS — Programmable Smart Power Management & Supervisor

CTW-SPMS is an all-digital power-management and supervision controller
implemented in synthesizable RTL for Tiny Tapeout TTSKY26c / SKY130.

## How it works

The frozen architecture consists of:

1. 8-bit digital power sample input through SPI
2. FIR power-sample filtering
3. Absolute power-deviation calculation
4. Persistent anomaly detection
5. HIGH / MEDIUM / LOW / CRITICAL classification
6. Four-rail startup sequencing
7. Two-flip-flop Power-Good synchronization
8. Power-Good stability qualification
9. Startup timeout supervision
10. Three-load priority management
11. Load shedding and staged restoration
12. Hard-fault shutdown
13. Fault latch and diagnostic logging
14. Watchdog supervision
15. Automatic retry and retry lockout
16. SPI configuration and status registers

The controller does not directly measure analog voltage or current.
External comparators, supervisors, ADCs or an MCU provide digital status
or measurement information.

## Safety behavior

Reset places the controller into a deterministic safe state:

- RAIL1_EN = 0
- RAIL2_EN = 0
- RAIL3_EN = 0
- RAIL4_EN = 0
- LOAD1_EN = 0
- LOAD2_EN = 0
- LOAD3_EN = 0

Critical faults will ultimately override normal control decisions and force
all rail and load enables OFF.

## Pin mapping

### Dedicated inputs

| Pin | Function |
|---|---|
| ui[0] | PG1 |
| ui[1] | PG2 |
| ui[2] | PG3 |
| ui[3] | PG4 |
| ui[4] | OVERCURRENT |
| ui[5] | OVERTEMP |
| ui[6] | WATCHDOG_IN |
| ui[7] | FORCE_SHUTDOWN |

### Dedicated outputs

| Pin | Function |
|---|---|
| uo[0] | RAIL1_EN |
| uo[1] | RAIL2_EN |
| uo[2] | RAIL3_EN |
| uo[3] | RAIL4_EN |
| uo[4] | LOAD1_EN |
| uo[5] | LOAD2_EN |
| uo[6] | LOAD3_EN |
| uo[7] | FAULT |

### Bidirectional interface

| Pin | Function |
|---|---|
| uio[0] | SPI_MISO |
| uio[1] | SPI_CS_N |
| uio[2] | SPI_SCLK |
| uio[3] | SPI_MOSI |

SPI is planned as Mode 0.

## How to test

The first repository milestone is a safe baseline implementation.

The baseline test verifies:

- deterministic reset behavior
- every rail enable is OFF
- every load enable is OFF
- FAULT defaults LOW
- unused bidirectional outputs remain disabled

Functional tests will be added incrementally with each CTW-SPMS subsystem.

## External hardware

A practical system can use:

- external ADC or MCU for digital power measurements
- voltage supervisors or comparators for PG signals
- DC/DC converter enable inputs connected to RAILx_EN
- load switches connected to LOADx_EN
- SPI master for configuration and diagnostics