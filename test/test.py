# SPDX-License-Identifier: Apache-2.0

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer


CLOCK_PERIOD_NS = 100  # 10 MHz
SPI_HALF_PERIOD_NS = 250  # 2 MHz SCLK, specified maximum

RAIL_MASK = 0x0F
LOAD_MASK = 0x70
FAULT_BIT = 0x80
SPI_MISO_BIT = 0x01
SPI_MISO_OE = 0x01

REG_POWER_SAMPLE = 0x00
REG_POWER_NOMINAL = 0x01
REG_WARN_THRESHOLD = 0x02
REG_FAULT_THRESHOLD = 0x03
REG_HIGH_THRESHOLD = 0x04
REG_MED_THRESHOLD = 0x05
REG_LOW_THRESHOLD = 0x06
REG_PG_STABLE = 0x07
REG_SEQUENCE_DELAY = 0x08
REG_STARTUP_TIMEOUT = 0x09
REG_WATCHDOG_TIMEOUT = 0x0A
REG_RETRY_DELAY = 0x0B
REG_MAX_RETRY = 0x0C
REG_CONTROL = 0x0D
REG_WARN_PERSIST = 0x0E
REG_FAULT_PERSIST = 0x0F
REG_STATUS = 0x10
REG_FILTERED_SAMPLE = 0x11
REG_DEVIATION = 0x12
REG_POWER_LEVEL = 0x13
REG_PG_STATUS = 0x14
REG_RAIL_STATUS = 0x15
REG_LOAD_STATUS = 0x16
REG_LAST_FAULT = 0x17
REG_FAULT_COUNT = 0x18
REG_RETRY_COUNT = 0x19
REG_CURRENT_STATE = 0x1A
REG_LAST_TIMEOUT_RAIL = 0x1B

CTRL_SYSTEM_ENABLE = 0x01
CTRL_CLEAR_FAULT = 0x02
CTRL_FORCE_SHUTDOWN = 0x04
CTRL_WATCHDOG_ENABLE = 0x08

FAULT_PG1 = 0x1
FAULT_PG2 = 0x2
FAULT_PG3 = 0x3
FAULT_PG4 = 0x4
FAULT_STARTUP_TIMEOUT = 0x5
FAULT_OVERCURRENT = 0x6
FAULT_OVERTEMP = 0x7
FAULT_POWER_ANOMALY = 0x8
FAULT_WATCHDOG_TIMEOUT = 0x9
FAULT_RETRY_EXHAUSTED = 0xA

ST_OFF = 0
ST_RUN = 9


def uio_value(cs_n=1, sclk=0, mosi=0):
    return ((cs_n & 1) << 1) | ((sclk & 1) << 2) | ((mosi & 1) << 3)


async def settle():
    await Timer(2, unit="ns")


async def start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())


async def reset_dut(dut, ena=1):
    dut.ena.value = ena
    dut.ui_in.value = 0
    dut.uio_in.value = uio_value(cs_n=1)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    await settle()
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
    await settle()


def byte_bits(value):
    return [(value >> shift) & 1 for shift in range(7, -1, -1)]


def bits_to_byte(bits):
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return value


async def spi_bits(dut, bits, release_cs=True):
    sampled = []
    dut.uio_in.value = uio_value(cs_n=0)
    await Timer(500, unit="ns")

    for bit in bits:
        dut.uio_in.value = uio_value(cs_n=0, sclk=0, mosi=bit)
        await Timer(SPI_HALF_PERIOD_NS, unit="ns")
        dut.uio_in.value = uio_value(cs_n=0, sclk=1, mosi=bit)
        await Timer(20, unit="ns")
        sampled.append(1 if (int(dut.uio_out.value) & SPI_MISO_BIT) else 0)
        await Timer(SPI_HALF_PERIOD_NS - 20, unit="ns")
        dut.uio_in.value = uio_value(cs_n=0, sclk=0, mosi=bit)

    await Timer(SPI_HALF_PERIOD_NS, unit="ns")
    if release_cs:
        dut.uio_in.value = uio_value(cs_n=1)
        await Timer(500, unit="ns")
    return sampled


async def spi_frame(dut, command, data=0, extra_bytes=None):
    bits = byte_bits(command) + byte_bits(data)
    for extra in extra_bytes or []:
        bits += byte_bits(extra)
    sampled = await spi_bits(dut, bits)
    return bits_to_byte(sampled[8:16])


async def write_reg(dut, address, value):
    await spi_frame(dut, address & 0x7F, value & 0xFF)


async def read_reg(dut, address):
    return await spi_frame(dut, 0x80 | (address & 0x7F), 0)


async def wait_for_mask(dut, mask, expected, cycles=100):
    for _ in range(cycles):
        await RisingEdge(dut.clk)
        await settle()
        if (int(dut.uo_out.value) & mask) == expected:
            return
    actual = int(dut.uo_out.value)
    raise AssertionError(
        f"output mask 0x{mask:02x} did not reach 0x{expected:02x}; got 0x{actual:02x}"
    )


def assert_output_invariants(dut):
    output = int(dut.uo_out.value)
    rails = output & RAIL_MASK
    if rails & 0x08:
        assert (rails & 0x07) == 0x07
    if rails & 0x04:
        assert (rails & 0x03) == 0x03
    if rails & 0x02:
        assert (rails & 0x01) == 0x01
    if output & FAULT_BIT:
        assert (output & (RAIL_MASK | LOAD_MASK)) == 0


async def configure_quiet_high_power(dut, sequence_delay=2):
    # x=64 settles to 96 because the frozen FIR has gain 6/4.
    await write_reg(dut, REG_WARN_THRESHOLD, 0xFF)
    await write_reg(dut, REG_FAULT_THRESHOLD, 0xFF)
    await write_reg(dut, REG_POWER_NOMINAL, 96)
    await write_reg(dut, REG_POWER_SAMPLE, 64)
    await write_reg(dut, REG_HIGH_THRESHOLD, 80)
    await write_reg(dut, REG_MED_THRESHOLD, 50)
    await write_reg(dut, REG_LOW_THRESHOLD, 20)
    await write_reg(dut, REG_PG_STABLE, 2)
    await write_reg(dut, REG_SEQUENCE_DELAY, sequence_delay)
    await write_reg(dut, REG_STARTUP_TIMEOUT, 80)


async def start_running(dut, sequence_delay=2):
    await configure_quiet_high_power(dut, sequence_delay)
    dut.ui_in.value = 0x0F
    await ClockCycles(dut.clk, 8)
    await write_reg(dut, REG_CONTROL, CTRL_SYSTEM_ENABLE)
    await wait_for_mask(dut, RAIL_MASK, RAIL_MASK, 80)
    for _ in range(80):
        if await read_reg(dut, REG_CURRENT_STATE) == ST_RUN:
            break
    else:
        raise AssertionError("sequencer did not reach RUN")


@cocotb.test()
async def test_reset_defaults_and_no_undefined_outputs(dut):
    """Covers reset, reset defaults, safe outputs and deterministic UIO OE."""
    await start_clock(dut)
    dut.ena.value = 1
    dut.ui_in.value = 0xFF
    dut.uio_in.value = uio_value(cs_n=1)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    await settle()

    assert dut.uo_out.value.is_resolvable
    assert dut.uio_out.value.is_resolvable
    assert dut.uio_oe.value.is_resolvable
    assert int(dut.uo_out.value) == 0
    assert int(dut.uio_out.value) == 0
    assert int(dut.uio_oe.value) == SPI_MISO_OE

    await reset_dut(dut)
    defaults = {
        REG_POWER_SAMPLE: 0x00,
        REG_POWER_NOMINAL: 0x80,
        REG_WARN_THRESHOLD: 0x10,
        REG_FAULT_THRESHOLD: 0x30,
        REG_HIGH_THRESHOLD: 0xC0,
        REG_MED_THRESHOLD: 0x80,
        REG_LOW_THRESHOLD: 0x40,
        REG_PG_STABLE: 0x03,
        REG_SEQUENCE_DELAY: 0x03,
        REG_STARTUP_TIMEOUT: 0x40,
        REG_WATCHDOG_TIMEOUT: 0x64,
        REG_RETRY_DELAY: 0x14,
        REG_MAX_RETRY: 0x03,
        REG_CONTROL: 0x00,
        REG_WARN_PERSIST: 0x03,
        REG_FAULT_PERSIST: 0x03,
    }
    for address, expected in defaults.items():
        assert await read_reg(dut, address) == expected
    assert int(dut.uo_out.value) == 0


@cocotb.test()
async def test_spi_protocol_back_to_back_abort_and_configuration(dut):
    """Covers SPI writes, reads, back-to-back frames, aborts and address isolation."""
    await start_clock(dut)
    await reset_dut(dut)

    await write_reg(dut, REG_POWER_SAMPLE, 0xA5)
    assert await read_reg(dut, REG_POWER_SAMPLE) == 0xA5
    await write_reg(dut, REG_POWER_SAMPLE, 0x5A)
    assert await read_reg(dut, REG_POWER_SAMPLE) == 0x5A

    partial = byte_bits(REG_POWER_SAMPLE) + byte_bits(0xC3)[:4]
    await spi_bits(dut, partial)
    assert await read_reg(dut, REG_POWER_SAMPLE) == 0x5A

    await write_reg(dut, 0x7E, 0xEE)
    assert await read_reg(dut, 0x7E) == 0x00
    assert await read_reg(dut, REG_POWER_SAMPLE) == 0x5A

    await spi_frame(dut, REG_POWER_SAMPLE, 0x96, extra_bytes=[0x69, 0xFF])
    assert await read_reg(dut, REG_POWER_SAMPLE) == 0x96

    await write_reg(dut, REG_PG_STABLE, 0x07)
    await write_reg(dut, REG_STARTUP_TIMEOUT, 0x22)
    assert await read_reg(dut, REG_PG_STABLE) == 0x07
    assert await read_reg(dut, REG_STARTUP_TIMEOUT) == 0x22


@cocotb.test()
async def test_fir_deviation_classifier_and_anomaly_persistence(dut):
    """Covers FIR, deviation, classifier, warning and severe persistence."""
    await start_clock(dut)
    await reset_dut(dut)
    dut.ui_in.value = 0x0F

    await write_reg(dut, REG_WARN_THRESHOLD, 0xFF)
    await write_reg(dut, REG_FAULT_THRESHOLD, 0xFF)
    await write_reg(dut, REG_POWER_NOMINAL, 96)
    await write_reg(dut, REG_POWER_SAMPLE, 64)
    await write_reg(dut, REG_HIGH_THRESHOLD, 80)
    await write_reg(dut, REG_MED_THRESHOLD, 50)
    await write_reg(dut, REG_LOW_THRESHOLD, 20)
    await ClockCycles(dut.clk, 6)
    assert await read_reg(dut, REG_FILTERED_SAMPLE) == 96
    assert await read_reg(dut, REG_DEVIATION) == 0
    assert await read_reg(dut, REG_POWER_LEVEL) == 3

    await write_reg(dut, REG_HIGH_THRESHOLD, 100)
    assert await read_reg(dut, REG_POWER_LEVEL) == 2

    await write_reg(dut, REG_WARN_THRESHOLD, 5)
    await write_reg(dut, REG_FAULT_THRESHOLD, 30)
    await write_reg(dut, REG_WARN_PERSIST, 3)
    await write_reg(dut, REG_FAULT_PERSIST, 0xFF)
    await write_reg(dut, REG_STARTUP_TIMEOUT, 0xFF)
    await write_reg(dut, REG_CONTROL, CTRL_SYSTEM_ENABLE)

    await write_reg(dut, REG_POWER_SAMPLE, 70)  # filtered=105, deviation=9
    assert (await read_reg(dut, REG_STATUS) & 0x04) != 0
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0

    # A bad interval shorter than the programmed persistence must not trip.
    await write_reg(dut, REG_POWER_SAMPLE, 96)  # filtered=144, deviation=48
    await write_reg(dut, REG_POWER_SAMPLE, 64)
    await ClockCycles(dut.clk, 8)
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0

    await write_reg(dut, REG_FAULT_PERSIST, 3)
    await write_reg(dut, REG_POWER_SAMPLE, 96)
    await wait_for_mask(dut, FAULT_BIT, FAULT_BIT, 20)
    assert await read_reg(dut, REG_LAST_FAULT) == FAULT_POWER_ANOMALY
    assert (int(dut.uo_out.value) & (RAIL_MASK | LOAD_MASK)) == 0


@cocotb.test()
async def test_pg_glitch_stability_and_zero_count(dut):
    """Covers 2-FF PG path, glitch rejection, stable acceptance and zero count."""
    await start_clock(dut)
    await reset_dut(dut)
    await write_reg(dut, REG_POWER_NOMINAL, 0)
    await write_reg(dut, REG_WARN_THRESHOLD, 0xFF)
    await write_reg(dut, REG_FAULT_THRESHOLD, 0xFF)
    await write_reg(dut, REG_PG_STABLE, 3)
    await write_reg(dut, REG_SEQUENCE_DELAY, 0)
    await write_reg(dut, REG_STARTUP_TIMEOUT, 0xFF)
    await write_reg(dut, REG_CONTROL, CTRL_SYSTEM_ENABLE)
    await wait_for_mask(dut, RAIL_MASK, 0x01, 20)

    dut.ui_in.value = 0x01
    await ClockCycles(dut.clk, 2)
    dut.ui_in.value = 0x00
    await ClockCycles(dut.clk, 8)
    assert await read_reg(dut, REG_PG_STATUS) == 0
    assert (int(dut.uo_out.value) & RAIL_MASK) == 0x01
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0

    dut.ui_in.value = 0x0F
    await wait_for_mask(dut, RAIL_MASK, 0x0F, 50)
    assert await read_reg(dut, REG_CURRENT_STATE) == ST_RUN

    await reset_dut(dut)
    await write_reg(dut, REG_POWER_NOMINAL, 0)
    await write_reg(dut, REG_WARN_THRESHOLD, 0xFF)
    await write_reg(dut, REG_FAULT_THRESHOLD, 0xFF)
    await write_reg(dut, REG_PG_STABLE, 0)
    await write_reg(dut, REG_SEQUENCE_DELAY, 0)
    dut.ui_in.value = 0x0F
    await ClockCycles(dut.clk, 4)
    await write_reg(dut, REG_CONTROL, CTRL_SYSTEM_ENABLE)
    await wait_for_mask(dut, RAIL_MASK, 0x0F, 30)
    assert await read_reg(dut, REG_CURRENT_STATE) == ST_RUN


@cocotb.test()
async def test_normal_startup_load_policy_recovery_shutdown_and_active_reset(dut):
    """Covers startup, shedding, staged restore, reverse shutdown, force and reset."""
    await start_clock(dut)
    await reset_dut(dut)
    await start_running(dut, sequence_delay=2)
    await wait_for_mask(dut, LOAD_MASK, LOAD_MASK, 30)

    # HIGH -> MEDIUM -> LOW -> CRITICAL shedding.
    await write_reg(dut, REG_POWER_SAMPLE, 40)  # filtered=60, MEDIUM
    await wait_for_mask(dut, LOAD_MASK, 0x30, 20)
    await write_reg(dut, REG_POWER_SAMPLE, 20)  # filtered=30, LOW
    await wait_for_mask(dut, LOAD_MASK, 0x10, 20)
    await write_reg(dut, REG_POWER_SAMPLE, 0)   # filtered=0, CRITICAL
    await wait_for_mask(dut, LOAD_MASK, 0x00, 20)

    # Recovery is one load at a time, separated by SEQUENCE_DELAY clocks.
    await write_reg(dut, REG_SEQUENCE_DELAY, 20)
    await write_reg(dut, REG_POWER_SAMPLE, 64)
    seen_loads = []
    for _ in range(80):
        await RisingEdge(dut.clk)
        value = int(dut.uo_out.value) & LOAD_MASK
        if not seen_loads or seen_loads[-1] != value:
            seen_loads.append(value)
        assert_output_invariants(dut)
        if value == LOAD_MASK:
            break
    assert seen_loads[-1] == LOAD_MASK
    assert all(v in (0x00, 0x10, 0x30, 0x70) for v in seen_loads)

    # FORCE_SHUTDOWN is immediate and does not create a fault.
    await write_reg(dut, REG_CONTROL, CTRL_SYSTEM_ENABLE | CTRL_FORCE_SHUTDOWN)
    assert (int(dut.uo_out.value) & (RAIL_MASK | LOAD_MASK | FAULT_BIT)) == 0
    await write_reg(dut, REG_CONTROL, CTRL_SYSTEM_ENABLE)
    await wait_for_mask(dut, RAIL_MASK, RAIL_MASK, 100)

    # Normal disable uses reverse rail order.
    await write_reg(dut, REG_SEQUENCE_DELAY, 10)
    await write_reg(dut, REG_CONTROL, 0)
    previous = int(dut.uo_out.value) & RAIL_MASK
    for _ in range(60):
        await RisingEdge(dut.clk)
        rails = int(dut.uo_out.value) & RAIL_MASK
        assert rails in (0x0F, 0x07, 0x03, 0x01, 0x00)
        assert rails <= previous
        previous = rails
        assert_output_invariants(dut)
        if rails == 0:
            break
    assert previous == 0

    # Reset asserted during active operation must override everything safely.
    await start_running(dut, sequence_delay=0)
    await wait_for_mask(dut, LOAD_MASK, LOAD_MASK, 20)
    dut.rst_n.value = 0
    await Timer(20, unit="ns")
    assert int(dut.uo_out.value) == 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
    assert int(dut.uo_out.value) == 0


@cocotb.test()
async def test_each_rail_startup_timeout_and_diagnostic(dut):
    """Covers PG1..PG4 startup timeout and failing-rail diagnostics."""
    await start_clock(dut)
    for failing_rail in range(1, 5):
        await reset_dut(dut)
        await write_reg(dut, REG_POWER_NOMINAL, 0)
        await write_reg(dut, REG_WARN_THRESHOLD, 0xFF)
        await write_reg(dut, REG_FAULT_THRESHOLD, 0xFF)
        await write_reg(dut, REG_PG_STABLE, 0)
        await write_reg(dut, REG_SEQUENCE_DELAY, 0)
        await write_reg(dut, REG_STARTUP_TIMEOUT, 3)
        dut.ui_in.value = (1 << (failing_rail - 1)) - 1
        await ClockCycles(dut.clk, 4)
        await write_reg(dut, REG_CONTROL, CTRL_SYSTEM_ENABLE)
        await wait_for_mask(dut, FAULT_BIT, FAULT_BIT, 50)
        assert await read_reg(dut, REG_LAST_FAULT) == FAULT_STARTUP_TIMEOUT
        assert await read_reg(dut, REG_LAST_TIMEOUT_RAIL) == failing_rail
        assert (int(dut.uo_out.value) & (RAIL_MASK | LOAD_MASK)) == 0


@cocotb.test()
async def test_each_pg_loss_during_run(dut):
    """Covers rail-specific PG1..PG4 loss faults during RUN."""
    await start_clock(dut)
    fault_codes = [FAULT_PG1, FAULT_PG2, FAULT_PG3, FAULT_PG4]
    for rail_index, expected_fault in enumerate(fault_codes):
        await reset_dut(dut)
        await start_running(dut, sequence_delay=0)
        dut.ui_in.value = 0x0F & ~(1 << rail_index)
        await wait_for_mask(dut, FAULT_BIT, FAULT_BIT, 20)
        assert await read_reg(dut, REG_LAST_FAULT) == expected_fault
        assert (int(dut.uo_out.value) & (RAIL_MASK | LOAD_MASK)) == 0


@cocotb.test()
async def test_external_fault_priority_latch_and_clear_semantics(dut):
    """Covers OC/OT priority, fault latch and safe CLEAR_FAULT semantics."""
    await start_clock(dut)
    await reset_dut(dut)

    # Simultaneous external faults: OVERCURRENT has explicit priority.
    dut.ui_in.value = (1 << 4) | (1 << 5)
    await wait_for_mask(dut, FAULT_BIT, FAULT_BIT, 10)
    assert await read_reg(dut, REG_LAST_FAULT) == FAULT_OVERCURRENT
    assert await read_reg(dut, REG_FAULT_COUNT) == 1

    # CLEAR_FAULT is ignored while any underlying hard-fault source remains.
    await write_reg(dut, REG_CONTROL, CTRL_CLEAR_FAULT)
    assert (int(dut.uo_out.value) & FAULT_BIT) != 0
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 5)
    assert (int(dut.uo_out.value) & FAULT_BIT) != 0
    await write_reg(dut, REG_CONTROL, CTRL_CLEAR_FAULT)
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0

    await reset_dut(dut)
    dut.ui_in.value = 1 << 5
    await wait_for_mask(dut, FAULT_BIT, FAULT_BIT, 10)
    assert await read_reg(dut, REG_LAST_FAULT) == FAULT_OVERTEMP
    assert (int(dut.uo_out.value) & (RAIL_MASK | LOAD_MASK)) == 0


@cocotb.test()
async def test_watchdog_heartbeat_and_timeout(dut):
    """Covers valid heartbeat toggles and watchdog timeout."""
    await start_clock(dut)
    await reset_dut(dut)
    await configure_quiet_high_power(dut, sequence_delay=0)
    await write_reg(dut, REG_WATCHDOG_TIMEOUT, 2)
    await write_reg(dut, REG_RETRY_DELAY, 0xFF)
    dut.ui_in.value = 0x0F
    await ClockCycles(dut.clk, 5)
    await write_reg(
        dut, REG_CONTROL, CTRL_SYSTEM_ENABLE | CTRL_WATCHDOG_ENABLE
    )
    await wait_for_mask(dut, RAIL_MASK, RAIL_MASK, 50)

    heartbeat = 0
    for _ in range(3):
        await ClockCycles(dut.clk, 700)
        heartbeat ^= 1
        dut.ui_in.value = 0x0F | (heartbeat << 6)
        await ClockCycles(dut.clk, 5)
        assert (int(dut.uo_out.value) & FAULT_BIT) == 0

    await ClockCycles(dut.clk, 2300)
    await wait_for_mask(dut, FAULT_BIT, FAULT_BIT, 20)
    assert await read_reg(dut, REG_LAST_FAULT) == FAULT_WATCHDOG_TIMEOUT
    assert (int(dut.uo_out.value) & (RAIL_MASK | LOAD_MASK)) == 0


@cocotb.test()
async def test_auto_retry_success_exhaustion_and_lock(dut):
    """Covers retry success, failed restart, exhaustion and FAULT_LOCK."""
    await start_clock(dut)
    await reset_dut(dut)
    await start_running(dut, sequence_delay=0)
    await write_reg(dut, REG_RETRY_DELAY, 0)
    await write_reg(dut, REG_MAX_RETRY, 2)

    dut.ui_in.value = 0x1F
    await wait_for_mask(dut, FAULT_BIT, FAULT_BIT, 10)
    dut.ui_in.value = 0x0F
    await ClockCycles(dut.clk, 1300)
    await wait_for_mask(dut, RAIL_MASK, RAIL_MASK, 80)
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0
    assert await read_reg(dut, REG_RETRY_COUNT) == 1
    assert await read_reg(dut, REG_LAST_FAULT) == FAULT_OVERCURRENT

    # Missing PG1 causes every restart to fail and eventually locks safely.
    await reset_dut(dut)
    await write_reg(dut, REG_POWER_NOMINAL, 0)
    await write_reg(dut, REG_WARN_THRESHOLD, 0xFF)
    await write_reg(dut, REG_FAULT_THRESHOLD, 0xFF)
    await write_reg(dut, REG_PG_STABLE, 0)
    await write_reg(dut, REG_SEQUENCE_DELAY, 0)
    await write_reg(dut, REG_STARTUP_TIMEOUT, 1)
    await write_reg(dut, REG_RETRY_DELAY, 0)
    await write_reg(dut, REG_MAX_RETRY, 1)
    dut.ui_in.value = 0
    await write_reg(dut, REG_CONTROL, CTRL_SYSTEM_ENABLE)
    await ClockCycles(dut.clk, 2600)
    status = await read_reg(dut, REG_STATUS)
    assert (status & 0x10) != 0  # FAULT_LOCK
    assert await read_reg(dut, REG_LAST_FAULT) == FAULT_RETRY_EXHAUSTED
    assert await read_reg(dut, REG_RETRY_COUNT) == 1
    assert (int(dut.uo_out.value) & (RAIL_MASK | LOAD_MASK)) == 0
    assert (int(dut.uo_out.value) & FAULT_BIT) != 0

    # Clear lock is permitted only after the active source is absent.
    await write_reg(dut, REG_CONTROL, CTRL_CLEAR_FAULT)
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0


@cocotb.test()
async def test_zero_boundaries_fault_count_saturation_and_illegal_state(dut):
    """Covers zero/minimum configuration, retry limit zero and safe recovery."""
    await start_clock(dut)
    await reset_dut(dut)
    await write_reg(dut, REG_POWER_NOMINAL, 0)
    await write_reg(dut, REG_WARN_THRESHOLD, 0xFF)
    await write_reg(dut, REG_FAULT_THRESHOLD, 0xFF)
    await write_reg(dut, REG_PG_STABLE, 0)
    await write_reg(dut, REG_SEQUENCE_DELAY, 0)
    await write_reg(dut, REG_STARTUP_TIMEOUT, 0)
    await write_reg(dut, REG_RETRY_DELAY, 0)
    await write_reg(dut, REG_MAX_RETRY, 0)
    await write_reg(dut, REG_CONTROL, CTRL_SYSTEM_ENABLE)
    await wait_for_mask(dut, FAULT_BIT, FAULT_BIT, 20)
    assert await read_reg(dut, REG_LAST_FAULT) == FAULT_RETRY_EXHAUSTED
    assert (await read_reg(dut, REG_STATUS) & 0x10) != 0
    assert (int(dut.uo_out.value) & (RAIL_MASK | LOAD_MASK)) == 0

    if os.getenv("GATES", "no") != "yes":
        # Saturation and illegal-state recovery are targeted at RTL internals.
        await reset_dut(dut)
        dut.user_project.u_fault_controller.fault_count.value = 0xFE
        dut.ui_in.value = 1 << 4
        await ClockCycles(dut.clk, 5)
        assert int(dut.user_project.fault_count.value) == 0xFF
        await ClockCycles(dut.clk, 5)
        assert int(dut.user_project.fault_count.value) == 0xFF

        await reset_dut(dut)
        dut.user_project.u_rail_sequencer.current_state.value = 0x1F
        await ClockCycles(dut.clk, 2)
        assert int(dut.user_project.current_state.value) == ST_OFF
        assert (int(dut.uo_out.value) & (RAIL_MASK | LOAD_MASK)) == 0
