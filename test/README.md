# CTW-SPMS verification

The Cocotb regression is shared by RTL and gate-level simulation.

Coverage includes:

- reset and active reset, including deterministic outputs and `uio_oe`
- complete SPI register/status access, incomplete aborts, extra clocks,
  unsupported addresses, back-to-back frames, and configuration effects
- first-sample-filled unity-gain FIR, FIR-valid classifier gating, deviation,
  exact classifier boundaries, per-write anomaly persistence, and transient
  rejection
- explicit two-flip-flop PG synchronization, symmetric 100 us stability
  qualification, glitches, and zero count
- normal startup/reverse shutdown, external force shutdown, Tiny Tapeout
  `ena` safety gating, and every rail timeout/RUN PG loss
- HIGH/MEDIUM/LOW/CRITICAL load policy and staged restoration
- frozen simultaneous-fault priority, OC/OT, latch and safe clear semantics
- RUN-only watchdog heartbeat/timeout and retry
  success/failure/exhaustion/FAULT_LOCK with root-cause retention
- zero boundaries, diagnostic saturation, illegal rail-state recovery, and
  safety invariants

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
