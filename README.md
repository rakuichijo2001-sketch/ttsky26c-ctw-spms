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
- Top module: `tt_um_ctw_spms`
- Target clock: 10 MHz

## Frozen architecture

POWER_SAMPLE -> FIR filter -> Power deviation -> Anomaly detector -> Power-level
classifier -> 4-rail sequencer -> 3-load priority manager -> Fault manager ->
Safe outputs.

The frozen architecture is implemented incrementally so every subsystem can be
regression-tested and hardened before integration.

## Current implementation — Milestone 1A

Milestone 1A adds the real SPI ingress and the first programmable register while
preserving the safe clocked foundation:

- one 10 MHz core clock domain
- shared divide-by-1000 clock-enable timebase (`timer_tick_ce`) at 10 kHz / 100 us
- reusable two-flip-flop synchronizers
- synchronized PG1..PG4, OVERCURRENT, OVERTEMP, WATCHDOG_IN,
  FORCE_SHUTDOWN_EXT and `ena`
- reset-only hard-fault latch for synchronized OVERCURRENT or OVERTEMP
- SPI Mode 0, MSB first, maximum supported SCLK 2 MHz
- synchronized SPI_CS_N, SPI_SCLK and SPI_MOSI; no SCLK-derived RTL clock
- exactly 16 SCLK cycles per accepted frame
- `0x00 POWER_SAMPLE` read/write support
- complete write updates POWER_SAMPLE atomically with a one-core-cycle strobe
- incomplete frames are aborted by CS_N HIGH
- extra clocks after a complete frame are ignored until CS_N returns HIGH

No generated clock or RTL clock gating is used.

## SPI protocol

The first byte contains the operation and 7-bit register address:

- bit7 = 0: WRITE
- bit7 = 1: READ
- bits6:0 = address

The second byte is write data or read data. In Milestone 1A only address `0x00`
is implemented. Unsupported reads return zero and unsupported writes do not
modify POWER_SAMPLE.

UIO mapping:

- `uio[0]`: SPI_MISO (output)
- `uio[1]`: SPI_CS_N (input)
- `uio[2]`: SPI_SCLK (input)
- `uio[3]`: SPI_MOSI (input)
- `uio[4..7]`: unused

`uio_oe = 8'h01`, so only MISO is driven.

## Safety behavior

RAIL1_EN..RAIL4_EN and LOAD1_EN..LOAD3_EN remain OFF in Milestone 1A.
`uo_out[7]` is FAULT and latches HIGH after synchronized OVERCURRENT or OVERTEMP.
Removing the source does not clear FAULT; reset remains the only clear mechanism
until the dedicated fault-management milestone.

## ASIC RTL policy

- deterministic active-low reset
- no functional `initial` blocks in `src/`
- no synthesizable `#` delays
- no implicit nets
- explicit widths and single primary clock domain
- asynchronous external controls synchronized before use
- clock-enable timing instead of divided/generated clocks
- no inferred latch or FPGA primitive
- no meaningless filler logic

## Verification

The Cocotb regression covers reset safety, hard-fault synchronization/latching,
2 MHz Mode-0 SPI write/read, POWER_SAMPLE reset behavior, exact one-cycle write
strobe at RTL, incomplete-frame abort, unsupported address behavior, extra-clock
ignore behavior, deterministic MISO direction, and permanently disabled rails and
loads.

FIR, anomaly/classifier, rail sequencing, load management, watchdog timeout,
auto-retry and full diagnostics remain staged for later milestones.

## License

Apache-2.0 unless otherwise noted.
