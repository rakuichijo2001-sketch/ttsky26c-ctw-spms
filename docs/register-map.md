# CTW-SPMS authoritative register map

All registers are eight bits wide and use the 7-bit SPI address from the first
transaction byte. Configuration registers are readable as well as writable.
Reserved addresses read as zero and ignore writes.

## Configuration and command registers

| Address | Name | Reset | Access | Meaning |
|---:|---|---:|---|---|
| `0x00` | POWER_SAMPLE | `0x00` | R/W | Unsigned external power-quality sample |
| `0x01` | POWER_NOMINAL | `0x80` | R/W | Nominal value for absolute deviation |
| `0x02` | ANOMALY_WARN_THRESHOLD | `0x10` | R/W | Warning deviation threshold |
| `0x03` | ANOMALY_FAULT_THRESHOLD | `0x30` | R/W | Severe deviation threshold |
| `0x04` | POWER_HIGH_THRESHOLD | `0xC0` | R/W | HIGH lower bound |
| `0x05` | POWER_MED_THRESHOLD | `0x80` | R/W | MEDIUM lower bound |
| `0x06` | POWER_LOW_THRESHOLD | `0x40` | R/W | LOW lower bound |
| `0x07` | PG_STABLE_COUNT | `0x03` | R/W | Consecutive 10 MHz clocks for PG assertion |
| `0x08` | SEQUENCE_DELAY | `0x03` | R/W | Core clocks between rail/load restoration stages |
| `0x09` | STARTUP_TIMEOUT | `0x40` | R/W | Core clocks allowed in an unqualified WAIT_PG state |
| `0x0A` | WATCHDOG_TIMEOUT | `0x64` | R/W | Watchdog limit in 100 us ticks |
| `0x0B` | RETRY_DELAY | `0x14` | R/W | Fault retry delay in 100 us ticks |
| `0x0C` | MAX_RETRY | `0x03` | R/W | Maximum attempts in one retry episode |
| `0x0D` | CONTROL | `0x00` | R/W* | System commands and persistent control bits |
| `0x0E` | WARN_PERSIST_COUNT | `0x03` | R/W | Consecutive warning samples required |
| `0x0F` | FAULT_PERSIST_COUNT | `0x03` | R/W | Consecutive severe samples required |

`CONTROL` bits:

| Bit | Name | Behavior |
|---:|---|---|
| 0 | SYSTEM_ENABLE | Persistent; requests startup when `ena` is active |
| 1 | CLEAR_FAULT | Write-one command pulse; reads zero |
| 2 | FORCE_SHUTDOWN | Persistent immediate safe-output request |
| 3 | WATCHDOG_ENABLE | Persistent watchdog enable |
| 7:4 | reserved | Read zero; writes ignored |

A write to CONTROL replaces bits 0, 2, and 3. Software that issues
CLEAR_FAULT while retaining other controls must include their desired values in
the same byte. CLEAR_FAULT is ignored while a qualified level fault remains.

## Status and diagnostics registers

| Address | Name | Access | Meaning |
|---:|---|---|---|
| `0x10` | STATUS | R | Summary flags described below |
| `0x11` | FILTERED_SAMPLE | R | Saturated eight-bit FIR result |
| `0x12` | POWER_DEVIATION | R | Unsigned absolute deviation |
| `0x13` | POWER_LEVEL | R | Bits 1:0: CRITICAL=0, LOW=1, MEDIUM=2, HIGH=3 |
| `0x14` | PG_STATUS | R | Bits 3:0: qualified PG4..PG1 |
| `0x15` | RAIL_STATUS | R | Bits 3:0: final RAIL4_EN..RAIL1_EN |
| `0x16` | LOAD_STATUS | R | Bits 2:0: final LOAD3_EN..LOAD1_EN |
| `0x17` | LAST_FAULT | R | Four-bit fault code |
| `0x18` | FAULT_COUNT | R | Saturating accepted-fault count |
| `0x19` | RETRY_COUNT | R | Attempts in the current/last retry episode |
| `0x1A` | CURRENT_STATE | R | Five-bit rail-sequencer state |
| `0x1B` | LAST_TIMEOUT_RAIL | R | Rail number 1..4 for the last startup timeout |

`STATUS` bits:

| Bit | Name |
|---:|---|
| 0 | stored SYSTEM_ENABLE |
| 1 | sequencer RUN |
| 2 | qualified anomaly warning |
| 3 | latched FAULT |
| 4 | FAULT_LOCK |
| 5 | internal or external force shutdown active |
| 6 | stored WATCHDOG_ENABLE |
| 7 | synchronized Tiny Tapeout `ena` |

## Fault codes

| Code | Meaning |
|---:|---|
| `0x0` | NONE |
| `0x1` | PG1_LOSS |
| `0x2` | PG2_LOSS |
| `0x3` | PG3_LOSS |
| `0x4` | PG4_LOSS |
| `0x5` | STARTUP_TIMEOUT; inspect `0x1B` for the rail |
| `0x6` | OVERCURRENT |
| `0x7` | OVERTEMP |
| `0x8` | POWER_ANOMALY |
| `0x9` | WATCHDOG_TIMEOUT |
| `0xA` | RETRY_EXHAUSTED |

## Rail sequencer states

| Value | State |
|---:|---|
| 0 | OFF |
| 1 | RAIL1_START |
| 2 | WAIT_PG1 |
| 3 | RAIL2_START |
| 4 | WAIT_PG2 |
| 5 | RAIL3_START |
| 6 | WAIT_PG3 |
| 7 | RAIL4_START |
| 8 | WAIT_PG4 |
| 9 | RUN |
| 10 | SHUTDOWN_R4 |
| 11 | SHUTDOWN_R3 |
| 12 | SHUTDOWN_R2 |
| 13 | SHUTDOWN_R1 |
| 14 | FAULT |

## Zero-value rules

- `PG_STABLE_COUNT=0` or 1 accepts the first synchronized HIGH sample.
- `SEQUENCE_DELAY=0` advances on the next clock in the applicable state.
- `STARTUP_TIMEOUT=0` faults on the first WAIT_PG clock if PG is not good.
- either anomaly persistence count set to 0 or 1 qualifies its first matching
  sample.
- `WATCHDOG_TIMEOUT=0` times out on the first enabled 100 us tick without a
  heartbeat edge.
- `RETRY_DELAY=0` evaluates recovery on the next 100 us tick.
- `MAX_RETRY=0` enters FAULT_LOCK immediately when a fault is accepted.
