# SPDX-License-Identifier: Apache-2.0

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer


CLOCK_PERIOD_NS = 100  # 10 MHz
SPI_HALF_PERIOD_NS = 250  # 2 MHz SCLK, specified maximum
FAULT_BIT = 0x80
POWER_OUTPUT_MASK = 0x7F
SPI_MISO_BIT = 0x01
SPI_MISO_OE = 0x01


def uio_value(cs_n=1, sclk=0, mosi=0):
    return ((cs_n & 1) << 1) | ((sclk & 1) << 2) | ((mosi & 1) << 3)


async def settle():
    # Covers gate-level UNIT_DELAY as well as RTL delta cycles.
    await Timer(2, unit="ns")


async def start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())


async def reset_dut(dut, ena=1):
    dut.ena.value = ena
    dut.ui_in.value = 0
    dut.uio_in.value = uio_value(cs_n=1, sclk=0, mosi=0)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    await settle()
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 4)
    await settle()


async def spi_bits(dut, bits, release_cs=True):
    """Drive Mode-0 bits at the specified 2 MHz maximum SCLK."""
    sampled = []

    dut.uio_in.value = uio_value(cs_n=0, sclk=0, mosi=0)
    # Give synchronized CS_N ample setup before the first clock.
    await Timer(500, unit="ns")

    for bit in bits:
        dut.uio_in.value = uio_value(cs_n=0, sclk=0, mosi=bit)
        await Timer(SPI_HALF_PERIOD_NS, unit="ns")

        dut.uio_in.value = uio_value(cs_n=0, sclk=1, mosi=bit)
        # CPHA=0: sample shortly after the physical rising edge, before the
        # core-domain detector prepares the following MISO bit.
        await Timer(20, unit="ns")
        sampled.append(1 if (int(dut.uio_out.value) & SPI_MISO_BIT) else 0)
        await Timer(SPI_HALF_PERIOD_NS - 20, unit="ns")

        dut.uio_in.value = uio_value(cs_n=0, sclk=0, mosi=bit)

    # One low half-cycle also provides normal CS hold time.
    await Timer(SPI_HALF_PERIOD_NS, unit="ns")

    if release_cs:
        dut.uio_in.value = uio_value(cs_n=1, sclk=0, mosi=0)
        await Timer(500, unit="ns")

    return sampled


def byte_bits(value):
    return [(value >> shift) & 1 for shift in range(7, -1, -1)]


def bits_to_byte(bits):
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return value


async def spi_frame(dut, command, data=0x00, extra_bytes=None):
    bits = byte_bits(command) + byte_bits(data)
    for extra in extra_bytes or []:
        bits += byte_bits(extra)
    sampled = await spi_bits(dut, bits, release_cs=True)
    return bits_to_byte(sampled[8:16])


async def monitor_strobe_cycles(dut, cycles):
    count = 0
    for _ in range(cycles):
        await RisingEdge(dut.clk)
        await settle()
        if int(dut.user_project.power_sample_wr_strobe.value):
            count += 1
    return count


@cocotb.test()
async def test_reset_and_safe_outputs(dut):
    await start_clock(dut)

    dut.ena.value = 1
    dut.ui_in.value = 0xFF
    dut.uio_in.value = uio_value(cs_n=1)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    await settle()

    assert int(dut.uo_out.value) == 0x00
    assert int(dut.uio_out.value) == 0x00
    assert int(dut.uio_oe.value) == SPI_MISO_OE

    await reset_dut(dut)
    assert (int(dut.uo_out.value) & POWER_OUTPUT_MASK) == 0x00
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0x00
    assert int(dut.uio_out.value) == 0x00
    assert int(dut.uio_oe.value) == SPI_MISO_OE

    # POWER_SAMPLE reset default is zero and is readable over SPI.
    assert await spi_frame(dut, 0x80, 0x00) == 0x00


@cocotb.test()
async def test_hard_fault_latch_preserved(dut):
    await start_clock(dut)
    await reset_dut(dut)

    # OVERTEMP ui[5] passes through 2FF CDC before setting FAULT.
    dut.ui_in.value = 1 << 5
    await ClockCycles(dut.clk, 2)
    await settle()
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0x00

    await ClockCycles(dut.clk, 2)
    await settle()
    assert (int(dut.uo_out.value) & FAULT_BIT) == FAULT_BIT
    assert (int(dut.uo_out.value) & POWER_OUTPUT_MASK) == 0x00

    # Removing source does not clear the Milestone-0.1 latch.
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 6)
    await settle()
    assert (int(dut.uo_out.value) & FAULT_BIT) == FAULT_BIT

    await reset_dut(dut)
    dut.ui_in.value = 1 << 4  # OVERCURRENT
    await ClockCycles(dut.clk, 4)
    await settle()
    assert (int(dut.uo_out.value) & FAULT_BIT) == FAULT_BIT
    assert (int(dut.uo_out.value) & POWER_OUTPUT_MASK) == 0x00
    assert int(dut.uio_oe.value) == SPI_MISO_OE


@cocotb.test()
async def test_spi_write_read_power_sample_at_2mhz(dut):
    await start_clock(dut)
    await reset_dut(dut)

    # WRITE: bit7=0, address=0x00, second byte=data.
    if os.getenv("GATES", "no") != "yes":
        monitor = cocotb.start_soon(monitor_strobe_cycles(dut, 140))
    await spi_frame(dut, 0x00, 0xA5)
    await ClockCycles(dut.clk, 4)

    if os.getenv("GATES", "no") != "yes":
        assert await monitor == 1, "POWER_SAMPLE write strobe must be exactly one core cycle"

    # READ: bit7=1, address=0x00. MISO returns current POWER_SAMPLE MSB first.
    assert await spi_frame(dut, 0x80, 0x00) == 0xA5

    await spi_frame(dut, 0x00, 0x5A)
    assert await spi_frame(dut, 0x80, 0x00) == 0x5A

    assert (int(dut.uo_out.value) & POWER_OUTPUT_MASK) == 0x00
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0x00


@cocotb.test()
async def test_spi_abort_unsupported_and_extra_clocks(dut):
    await start_clock(dut)
    await reset_dut(dut)

    await spi_frame(dut, 0x00, 0x3C)
    assert await spi_frame(dut, 0x80, 0x00) == 0x3C

    # Incomplete 12-clock write must abort when CS_N returns HIGH.
    partial = byte_bits(0x00) + byte_bits(0xC3)[:4]
    await spi_bits(dut, partial, release_cs=True)
    assert await spi_frame(dut, 0x80, 0x00) == 0x3C

    # Unsupported write address must not corrupt POWER_SAMPLE.
    await spi_frame(dut, 0x01, 0xEE)
    assert await spi_frame(dut, 0x80, 0x00) == 0x3C

    # Unsupported reads are deterministic zero in this minimal register path.
    assert await spi_frame(dut, 0x81, 0x00) == 0x00

    # Once sixteen clocks complete, additional clocks under the same CS_N are
    # ignored until CS_N returns HIGH. They must not create a second write.
    await spi_frame(dut, 0x00, 0x96, extra_bytes=[0x69, 0xFF])
    assert await spi_frame(dut, 0x80, 0x00) == 0x96

    assert int(dut.uio_oe.value) == SPI_MISO_OE
    assert (int(dut.uo_out.value) & POWER_OUTPUT_MASK) == 0x00
