# CTW-SPMS verification

The Cocotb regression is shared by RTL and gate-level simulation.

Current Milestone 1A coverage includes:

- deterministic reset and safe rail/load outputs
- synchronized OVERCURRENT / OVERTEMP fault latching
- SPI Mode 0 at the specified 2 MHz maximum SCLK
- `0x00 POWER_SAMPLE` write and read
- one-core-cycle POWER_SAMPLE write strobe in RTL
- incomplete-frame abort on CS_N HIGH
- unsupported write isolation and deterministic zero reads
- extra-clock ignore behavior after a complete frame
- deterministic `uio_oe` with only SPI_MISO driven

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
