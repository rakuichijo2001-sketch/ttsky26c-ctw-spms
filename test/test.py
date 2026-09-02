# SPDX-License-Identifier: Apache-2.0

import cocotb

from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer


CLOCK_PERIOD_NS = 100  # 10 MHz
FAULT_BIT = 0x80
POWER_OUTPUT_MASK = 0x7F
MISO_DATA_BIT = 0x01


async def settle():
    # Covers gate-level UNIT_DELAY as well as RTL delta cycles.
    await Timer(2, unit="ns")


async def reset_dut(dut, ena=1):
    dut.ena.value = ena
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    await settle()
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 3)
    await settle()


async def start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())


async def wait_for_miso_high(dut, limit_cycles=1100):
    for cycle in range(1, limit_cycles + 1):
        await RisingEdge(dut.clk)
        await settle()
        if int(dut.uio_out.value) & MISO_DATA_BIT:
            return cycle
    raise AssertionError("uio_out[0] did not go high within expected window")


@cocotb.test()
async def test_reset_and_no_fault_safe_state(dut):
    await start_clock(dut)

    dut.ena.value = 1
    dut.ui_in.value = 0xFF
    dut.uio_in.value = 0xFF
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    await settle()

    assert int(dut.uo_out.value) == 0x00
    assert int(dut.uio_out.value) == 0x00
    assert int(dut.uio_oe.value) == 0x00

    await reset_dut(dut)
    await ClockCycles(dut.clk, 10)
    await settle()

    assert (int(dut.uo_out.value) & POWER_OUTPUT_MASK) == 0x00
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0x00
    assert int(dut.uio_oe.value) == 0x00
    assert 0 <= int(dut.uio_out.value) <= 0x01


@cocotb.test()
async def test_hard_fault_latch_and_reset(dut):
    await start_clock(dut)
    await reset_dut(dut)

    # OVERTEMP is ui_in[5]. Two synchronizer flops plus the latch mean
    # FAULT must not assert immediately, then must assert deterministically.
    dut.ui_in.value = 1 << 5
    await ClockCycles(dut.clk, 2)
    await settle()
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0x00

    await ClockCycles(dut.clk, 1)
    await settle()
    assert (int(dut.uo_out.value) & FAULT_BIT) == FAULT_BIT
    assert (int(dut.uo_out.value) & POWER_OUTPUT_MASK) == 0x00

    # Removing the source must not clear the latch.
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 6)
    await settle()
    assert (int(dut.uo_out.value) & FAULT_BIT) == FAULT_BIT

    # Reset is the only clear mechanism in Milestone 0.1.
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    await settle()
    assert int(dut.uo_out.value) == 0x00
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 3)
    await settle()

    # OVERCURRENT is ui_in[4].
    dut.ui_in.value = 1 << 4
    await ClockCycles(dut.clk, 3)
    await settle()
    assert (int(dut.uo_out.value) & FAULT_BIT) == FAULT_BIT
    assert (int(dut.uo_out.value) & POWER_OUTPUT_MASK) == 0x00
    assert int(dut.uio_oe.value) == 0x00


@cocotb.test()
async def test_timebase_is_10khz_one_cycle_enable(dut):
    await start_clock(dut)
    await reset_dut(dut)

    # With no PG/watchdog readiness, uio_out[0] mirrors timer_tick_ce.
    await wait_for_miso_high(dut)

    await RisingEdge(dut.clk)
    await settle()
    assert (int(dut.uio_out.value) & MISO_DATA_BIT) == 0x00

    # Consecutive rising edges of a divide-by-1000 enable are exactly
    # 1000 core-clock cycles apart.
    cycles_to_next_tick = await wait_for_miso_high(dut, limit_cycles=1000)
    assert cycles_to_next_tick == 999

    await RisingEdge(dut.clk)
    await settle()
    assert (int(dut.uio_out.value) & MISO_DATA_BIT) == 0x00
    assert int(dut.uio_oe.value) == 0x00


@cocotb.test()
async def test_pg_watchdog_force_shutdown_foundation_path(dut):
    await start_clock(dut)
    await reset_dut(dut)

    # All PG inputs good; toggle WATCHDOG_IN to create retained status.
    dut.ui_in.value = 0x0F
    await ClockCycles(dut.clk, 4)
    dut.ui_in.value = 0x4F
    await ClockCycles(dut.clk, 4)
    await settle()

    # Wait for the timebase pulse, then one more core edge lets the
    # readiness register consume timer_tick_ce.
    await wait_for_miso_high(dut)
    await RisingEdge(dut.clk)
    await settle()
    assert (int(dut.uio_out.value) & MISO_DATA_BIT) == MISO_DATA_BIT
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0x00
    assert (int(dut.uo_out.value) & POWER_OUTPUT_MASK) == 0x00

    # FORCE_SHUTDOWN_EXT is synchronized and clears real readiness state,
    # but it is not a hard-fault source and must not set FAULT.
    dut.ui_in.value = 0xCF
    await ClockCycles(dut.clk, 3)
    await settle()
    assert (int(dut.uio_out.value) & MISO_DATA_BIT) == 0x00
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0x00

    # Release FORCE_SHUTDOWN_EXT. With PG still good and watchdog status
    # retained, readiness must qualify again on a later timer tick.
    dut.ui_in.value = 0x4F
    await ClockCycles(dut.clk, 3)
    await wait_for_miso_high(dut)
    await RisingEdge(dut.clk)
    await settle()
    assert (int(dut.uio_out.value) & MISO_DATA_BIT) == MISO_DATA_BIT
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0x00

    # PG1 loss then clears readiness after synchronization without inventing
    # a Milestone-0.1 PG fault code.
    dut.ui_in.value = 0x4E
    await ClockCycles(dut.clk, 3)
    await settle()
    assert (int(dut.uio_out.value) & MISO_DATA_BIT) == 0x00
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0x00
    assert (int(dut.uo_out.value) & POWER_OUTPUT_MASK) == 0x00
    assert int(dut.uio_oe.value) == 0x00
