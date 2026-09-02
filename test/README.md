# CTW-SPMS verification

The Cocotb regression is shared by RTL and gate-level simulation.

Coverage includes:

- reset and active reset, including deterministic outputs and `uio_oe`
- complete SPI register/status access, incomplete aborts, extra clocks,
  unsupported addresses, back-to-back frames, and configuration effects
- FIR, deviation, classifier, anomaly persistence, and transient rejection
- PG synchronization, stability qualification, glitches, and zero count
- normal startup/reverse shutdown and every rail timeout/RUN PG loss
- HIGH/MEDIUM/LOW/CRITICAL load policy and staged restoration
- simultaneous-fault priority, OC/OT, latch and safe clear semantics
- watchdog heartbeat/timeout and retry success/failure/exhaustion/FAULT_LOCK
- zero boundaries, diagnostic saturation, illegal-state recovery, and safety
  invariants

Run RTL simulation with:

```sh
make -B
```

For gate-level simulation, use the netlist produced by the Tiny Tapeout GDS
workflow as `gate_level_netlist.v`, then run:

```sh
make -B GATES=yes
```

Waveforms are written to `tb.fst` and can be opened with GTKWave or Surfer.
