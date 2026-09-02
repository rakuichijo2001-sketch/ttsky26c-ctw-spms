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

The complete frozen architecture remains unchanged, but implementation is staged
so each foundation block can be verified and hardened before the next subsystem.

## Milestone 0.1 — real clocked ASIC foundation

Milestone 0.1 intentionally implements only the minimum real clocked control
foundation:

- one 10 MHz core clock domain
- a divide-by-1000 clock-enable timebase (`timer_tick_ce`) at 10 kHz / 100 us
- reusable two-flip-flop synchronizers
- synchronized PG1..PG4, OVERCURRENT, OVERTEMP, WATCHDOG_IN,
  FORCE_SHUTDOWN_EXT and `ena`
- a reset-only hard-fault latch for synchronized OVERCURRENT or OVERTEMP
- retained watchdog-transition status
- a future-compatible foundation-readiness state using synchronized PG,
  watchdog, FORCE_SHUTDOWN_EXT, `ena` and the timer tick

No generated clock or clock gating is used.

### Safety behavior

`uo_out[6:0]` remains permanently zero in this milestone, so RAIL1_EN..RAIL4_EN
and LOAD1_EN..LOAD3_EN are always OFF. `uo_out[7]` is FAULT and latches HIGH
only after synchronized OVERCURRENT or OVERTEMP. Removing the fault input does
not clear FAULT; reset is the only clear mechanism in Milestone 0.1.

FORCE_SHUTDOWN_EXT clears the internal foundation-readiness state but does not
set FAULT.

### UIO / SPI reservation

The frozen UIO mapping remains:

- `uio[0]`: SPI_MISO
- `uio[1]`: SPI_CS_N
- `uio[2]`: SPI_SCLK
- `uio[3]`: SPI_MOSI
- `uio[4..7]`: unused

SPI is not implemented in Milestone 0.1. `uio_oe` is always `8'h00`, so every
UIO remains an input. The internal MISO data path at `uio_out[0]` is deterministic
and is used only to verify the foundation: it reports foundation readiness, or
the one-core-cycle 10 kHz timer pulse while not ready. `uio_out[7:1]` is zero.

## ASIC RTL policy

- deterministic active-low reset
- no functional `initial` blocks in `src/`
- no `#delay` in `src/`
- no implicit nets
- explicit widths
- one primary clock domain
- asynchronous control inputs synchronized before use
- clock-enable timing instead of divided/generated clocks
- no inferred latch or FPGA primitive
- no dummy logic added for cell count

## Verification

The Cocotb regression checks reset safety, hard-fault synchronization and
latching, reset clearing, permanently-disabled rail/load outputs, deterministic
UIO behavior, the exact 10 kHz one-cycle timebase, and the synchronized
PG/watchdog/FORCE_SHUTDOWN_EXT readiness path.

Future FIR, SPI register bank, rail sequencing, load management, watchdog timeout,
retry and diagnostics remain outside Milestone 0.1.

## License

Apache-2.0 unless otherwise noted.
