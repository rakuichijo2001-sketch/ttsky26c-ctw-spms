# CTW-SPMS — Programmable Smart Power Management & Supervisor

CTW-SPMS is an all-digital power-management and supervision controller
implemented in synthesizable RTL for Tiny Tapeout TTSKY26c / SKY130.

## Current implementation: Milestone 1A

The 10 MHz Tiny Tapeout `clk` remains the only clock domain. `timebase_tick`
emits a one-core-cycle clock enable at 10 kHz, so one timer tick represents
100 us. It does not create a divided clock.

All asynchronous project status/control inputs remain behind 2-flip-flop
synchronizers. Synchronized OVERCURRENT and OVERTEMP set the existing fail-safe
FAULT latch; reset is the only clear mechanism at this stage.

Milestone 1A adds a core-clocked SPI slave. `SPI_CS_N`, `SPI_SCLK`, and `SPI_MOSI`
are synchronized into the 10 MHz clock domain, and SCLK edges are detected as
data events rather than used as an RTL clock.

## SPI ingress

SPI mode and framing:

- Mode 0 (CPOL=0, CPHA=0)
- MSB first
- maximum supported SCLK: 2 MHz
- CS_N LOW frames a transaction
- exactly 16 SCLK cycles form a complete transaction
- CS_N HIGH aborts an incomplete frame
- clocks beyond a completed frame are ignored until CS_N returns HIGH

First byte:

- bit7 = 0 WRITE, 1 READ
- bits6:0 = register address

Second byte:

- WRITE: data from MOSI
- READ: data on MISO

Milestone 1A implements address `0x00 POWER_SAMPLE`. A complete WRITE updates
POWER_SAMPLE atomically and generates a write strobe lasting exactly one core
clock. A READ returns the current POWER_SAMPLE. Unsupported reads return zero;
unsupported writes do not modify POWER_SAMPLE.

## Safety behavior

After reset:

- RAIL1_EN..RAIL4_EN = 0
- LOAD1_EN..LOAD3_EN = 0
- FAULT = 0
- POWER_SAMPLE = 0

After synchronized OVERCURRENT or OVERTEMP, FAULT latches HIGH while every rail
and load remains OFF.

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
| ui[7] | FORCE_SHUTDOWN_EXT |

### Dedicated outputs

| Pin | Function |
|---|---|
| uo[0] | RAIL1_EN (OFF in M1A) |
| uo[1] | RAIL2_EN (OFF in M1A) |
| uo[2] | RAIL3_EN (OFF in M1A) |
| uo[3] | RAIL4_EN (OFF in M1A) |
| uo[4] | LOAD1_EN (OFF in M1A) |
| uo[5] | LOAD2_EN (OFF in M1A) |
| uo[6] | LOAD3_EN (OFF in M1A) |
| uo[7] | FAULT |

### Bidirectional interface

| Pin | Function |
|---|---|
| uio[0] | SPI_MISO output |
| uio[1] | SPI_CS_N input |
| uio[2] | SPI_SCLK input |
| uio[3] | SPI_MOSI input |
| uio[4..7] | unused |

Only `uio[0]` is driven, so `uio_oe = 8'h01`.

## Verification

The self-checking Cocotb regression covers reset/safe outputs, hard-fault CDC
and latching, Mode-0 SPI at the full 2 MHz supported SCLK, POWER_SAMPLE read and
write, one-core-cycle write strobe at RTL, incomplete-frame abort, deterministic
unsupported reads, unsupported-write isolation, extra-clock ignore behavior,
and gate-level compatibility.
