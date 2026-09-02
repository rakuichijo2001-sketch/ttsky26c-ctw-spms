# SPDX-License-Identifier: Apache-2.0

import cocotb

from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


CLOCK_PERIOD_NS = 100  # 10 MHz


async def reset_dut(dut):
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0

    dut.rst_n.value = 0

    await ClockCycles(dut.clk, 5)

    dut.rst_n.value = 1

    await ClockCycles(dut.clk, 2)


@cocotb.test()
async def test_reset_safe_state(dut):
    """
    CTW-SPMS safety baseline.

    All rail and load enables must remain OFF during reset.
    """

    clock = Clock(
        dut.clk,
        CLOCK_PERIOD_NS,
        unit="ns",
    )

    cocotb.start_soon(clock.start())

    dut.ena.value = 1
    dut.ui_in.value = 0xFF
    dut.uio_in.value = 0xFF

    dut.rst_n.value = 0

    await ClockCycles(dut.clk, 3)

    assert int(dut.uo_out.value) == 0x00
    assert int(dut.uio_out.value) == 0x00
    assert int(dut.uio_oe.value) == 0x00


@cocotb.test()
async def test_baseline_outputs_safe(dut):
    """
    Baseline implementation intentionally keeps all power-control
    outputs disabled until functional subsystems are integrated.
    """

    clock = Clock(
        dut.clk,
        CLOCK_PERIOD_NS,
        unit="ns",
    )

    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    # Exercise every input.
    dut.ui_in.value = 0xFF
    dut.uio_in.value = 0xFF

    await ClockCycles(dut.clk, 5)

    # RAIL1..4, LOAD1..3 and FAULT all remain low.
    assert int(dut.uo_out.value) == 0x00

    # No UIO output is enabled yet.
    assert int(dut.uio_out.value) == 0x00
    assert int(dut.uio_oe.value) == 0x00