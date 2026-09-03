# SPDX-License-Identifier: Apache-2.0

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer


CLOCK_PERIOD_NS = 100
SPI_HALF_PERIOD_NS = 250
TICK_CYCLES = 1000

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
REG_FAULT_DETAIL = 0x1B
REG_VERSION = 0x1F

CTRL_SYSTEM_ENABLE = 0x01
CTRL_CLEAR_FAULT = 0x02
CTRL_FORCE_SHUTDOWN = 0x04
CTRL_WATCHDOG_ENABLE = 0x08

POWER_CRITICAL = 0
POWER_LOW = 1
POWER_MEDIUM = 2
POWER_HIGH = 3

FAULT_PG1 = 0x1
FAULT_PG2 = 0x2
FAULT_PG3 = 0x3
FAULT_PG4 = 0x4
FAULT_STARTUP_TIMEOUT = 0x5
FAULT_OVERCURRENT = 0x6
FAULT_OVERTEMP = 0x7
FAULT_POWER_ANOMALY = 0x8
FAULT_WATCHDOG_TIMEOUT = 0x9

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


async def write_repeated_sample(dut, value, count=4):
    for _ in range(count):
        await write_reg(dut, REG_POWER_SAMPLE, value)


async def wait_for_mask(dut, mask, expected, cycles=2000):
    for _ in range(cycles):
        await RisingEdge(dut.clk)
        await settle()
        if (int(dut.uo_out.value) & mask) == expected:
            return
    actual = int(dut.uo_out.value)
    raise AssertionError(
        f"mask 0x{mask:02x} did not reach 0x{expected:02x}; got 0x{actual:02x}"
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


async def configure_quiet_high_power(dut, sequence_delay=0):
    await write_reg(dut, REG_WARN_THRESHOLD, 0xFF)
    await write_reg(dut, REG_FAULT_THRESHOLD, 0xFF)
    await write_reg(dut, REG_POWER_NOMINAL, 200)
    await write_reg(dut, REG_POWER_SAMPLE, 200)
    await write_reg(dut, REG_HIGH_THRESHOLD, 192)
    await write_reg(dut, REG_MED_THRESHOLD, 128)
    await write_reg(dut, REG_LOW_THRESHOLD, 64)
    await write_reg(dut, REG_PG_STABLE, 0)
    await write_reg(dut, REG_SEQUENCE_DELAY, sequence_delay)
    await write_reg(dut, REG_STARTUP_TIMEOUT, 5)


async def start_running(dut, sequence_delay=0):
    await configure_quiet_high_power(dut, sequence_delay)
    dut.ui_in.value = 0x0F
    await write_reg(dut, REG_CONTROL, CTRL_SYSTEM_ENABLE)
    await wait_for_mask(dut, RAIL_MASK, RAIL_MASK, 2 * TICK_CYCLES)
    await ClockCycles(dut.clk, 5)
    assert await read_reg(dut, REG_CURRENT_STATE) == ST_RUN


@cocotb.test()
async def test_reset_defaults_version_and_no_undefined_outputs(dut):
    """Reset values, FIR-invalid state, deterministic outputs, and VERSION."""
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
        REG_FAULT_THRESHOLD: 0x20,
        REG_HIGH_THRESHOLD: 0xC0,
        REG_MED_THRESHOLD: 0x80,
        REG_LOW_THRESHOLD: 0x40,
        REG_PG_STABLE: 0x03,
        REG_SEQUENCE_DELAY: 0x05,
        REG_STARTUP_TIMEOUT: 0x64,
        REG_WATCHDOG_TIMEOUT: 0x64,
        REG_RETRY_DELAY: 0x32,
        REG_MAX_RETRY: 0x03,
        REG_CONTROL: 0x00,
        REG_WARN_PERSIST: 0x02,
        REG_FAULT_PERSIST: 0x03,
    }
    for address, expected in defaults.items():
        assert await read_reg(dut, address) == expected
    assert await read_reg(dut, REG_POWER_LEVEL) == POWER_CRITICAL
    assert await read_reg(dut, REG_VERSION) == 0x01
    assert int(dut.uo_out.value) == 0


@cocotb.test()
async def test_spi_protocol_atomic_write_abort_and_sample_strobe(dut):
    """SPI framing, atomic writes, abort, address isolation, and FIR hold."""
    await start_clock(dut)
    await reset_dut(dut)
    assert await read_reg(dut, REG_FILTERED_SAMPLE) == 0
    await write_reg(dut, REG_POWER_SAMPLE, 0xA5)
    assert await read_reg(dut, REG_POWER_SAMPLE) == 0xA5
    assert await read_reg(dut, REG_FILTERED_SAMPLE) == 0xA5
    await ClockCycles(dut.clk, 200)
    assert await read_reg(dut, REG_FILTERED_SAMPLE) == 0xA5

    partial = byte_bits(REG_POWER_SAMPLE) + byte_bits(0xC3)[:4]
    await spi_bits(dut, partial)
    assert await read_reg(dut, REG_POWER_SAMPLE) == 0xA5
    assert await read_reg(dut, REG_FILTERED_SAMPLE) == 0xA5

    await write_reg(dut, 0x7E, 0xEE)
    assert await read_reg(dut, 0x7E) == 0
    await spi_frame(dut, REG_POWER_SAMPLE, 0x5A, extra_bytes=[0x69, 0xFF])
    assert await read_reg(dut, REG_POWER_SAMPLE) == 0x5A
    assert await read_reg(dut, REG_FILTERED_SAMPLE) == 0x92


@cocotb.test()
async def test_fir_deviation_classifier_and_anomaly_per_write(dut):
    """Unity-gain FIR, first-sample fill, valid gating, persistence per write."""
    await start_clock(dut)
    await reset_dut(dut)
    await write_reg(dut, REG_POWER_NOMINAL, 100)
    await write_reg(dut, REG_HIGH_THRESHOLD, 110)
    await write_reg(dut, REG_MED_THRESHOLD, 90)
    await write_reg(dut, REG_LOW_THRESHOLD, 70)
    assert await read_reg(dut, REG_POWER_LEVEL) == POWER_CRITICAL

    await write_reg(dut, REG_POWER_SAMPLE, 100)
    assert await read_reg(dut, REG_FILTERED_SAMPLE) == 100
    assert await read_reg(dut, REG_DEVIATION) == 0
    assert await read_reg(dut, REG_POWER_LEVEL) == POWER_MEDIUM
    await write_reg(dut, REG_POWER_SAMPLE, 104)
    assert await read_reg(dut, REG_FILTERED_SAMPLE) == 101
    await write_reg(dut, REG_POWER_SAMPLE, 108)
    assert await read_reg(dut, REG_FILTERED_SAMPLE) == 103
    await write_reg(dut, REG_POWER_SAMPLE, 112)
    assert await read_reg(dut, REG_FILTERED_SAMPLE) == 106
    assert await read_reg(dut, REG_DEVIATION) == 6

    await write_reg(dut, REG_WARN_THRESHOLD, 5)
    await write_reg(dut, REG_FAULT_THRESHOLD, 20)
    await write_reg(dut, REG_WARN_PERSIST, 2)
    await write_reg(dut, REG_FAULT_PERSIST, 3)
    await write_reg(dut, REG_MAX_RETRY, 0)
    await write_reg(dut, REG_CONTROL, CTRL_SYSTEM_ENABLE)
    await write_reg(dut, REG_POWER_SAMPLE, 120)
    assert (await read_reg(dut, REG_STATUS) & 0x04) == 0
    await ClockCycles(dut.clk, 200)
    assert (await read_reg(dut, REG_STATUS) & 0x04) == 0
    await write_reg(dut, REG_POWER_SAMPLE, 120)
    assert (await read_reg(dut, REG_STATUS) & 0x04) != 0

    await write_reg(dut, REG_POWER_SAMPLE, 120)
    await write_reg(dut, REG_POWER_SAMPLE, 120)
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0
    await write_reg(dut, REG_POWER_SAMPLE, 120)
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0
    await write_reg(dut, REG_POWER_SAMPLE, 120)
    await wait_for_mask(dut, FAULT_BIT, FAULT_BIT, 20)
    assert await read_reg(dut, REG_LAST_FAULT) == FAULT_POWER_ANOMALY
    assert (int(dut.uo_out.value) & (RAIL_MASK | LOAD_MASK)) == 0


@cocotb.test()
async def test_classifier_boundaries_and_pg_two_flip_flop_sync(dut):
    """Exact classifier boundaries and the explicit two-stage PG synchronizer."""
    await start_clock(dut)

    boundary_cases = (
        (110, POWER_HIGH),
        (109, POWER_MEDIUM),
        (90, POWER_MEDIUM),
        (89, POWER_LOW),
        (70, POWER_LOW),
        (69, POWER_CRITICAL),
    )
    for sample, expected_level in boundary_cases:
        await reset_dut(dut)
        await write_reg(dut, REG_HIGH_THRESHOLD, 110)
        await write_reg(dut, REG_MED_THRESHOLD, 90)
        await write_reg(dut, REG_LOW_THRESHOLD, 70)
        await write_reg(dut, REG_POWER_SAMPLE, sample)
        assert await read_reg(dut, REG_POWER_LEVEL) == expected_level

    if os.getenv("GATES", "no") != "yes":
        await reset_dut(dut)
        assert int(dut.user_project.pg1_sync.value) == 0
        dut.ui_in.value = 0x01
        await RisingEdge(dut.clk)
        await settle()
        assert int(dut.user_project.pg1_sync.value) == 0
        await RisingEdge(dut.clk)
        await settle()
        assert int(dut.user_project.pg1_sync.value) == 1


@cocotb.test()
async def test_pg_tick_filter_glitches_and_sequence_delay(dut):
    """PG uses 100 us samples, rejects glitches, and gates startup."""
    await start_clock(dut)
    await reset_dut(dut)
    await configure_quiet_high_power(dut, sequence_delay=0)
    await write_reg(dut, REG_PG_STABLE, 3)
    await write_reg(dut, REG_STARTUP_TIMEOUT, 0)
    await write_reg(dut, REG_CONTROL, CTRL_SYSTEM_ENABLE)
    await wait_for_mask(dut, RAIL_MASK, 0x01, 30)

    dut.ui_in.value = 0x01
    await ClockCycles(dut.clk, 1500)
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 1500)
    assert await read_reg(dut, REG_PG_STATUS) == 0
    assert (int(dut.uo_out.value) & RAIL_MASK) == 0x01
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0

    dut.ui_in.value = 0x0F
    await wait_for_mask(dut, RAIL_MASK, RAIL_MASK, 4 * TICK_CYCLES)
    await ClockCycles(dut.clk, 5)
    assert await read_reg(dut, REG_CURRENT_STATE) == ST_RUN

    dut.ui_in.value = 0x0E
    await ClockCycles(dut.clk, 500)
    dut.ui_in.value = 0x0F
    await ClockCycles(dut.clk, 1500)
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0
    assert (int(dut.uo_out.value) & RAIL_MASK) == RAIL_MASK

    dut.ui_in.value = 0x0E
    await wait_for_mask(dut, FAULT_BIT, FAULT_BIT, 4 * TICK_CYCLES)
    assert await read_reg(dut, REG_LAST_FAULT) == FAULT_PG1

    await reset_dut(dut)
    await configure_quiet_high_power(dut, sequence_delay=2)
    dut.ui_in.value = 0x0F
    await ClockCycles(dut.clk, TICK_CYCLES + 20)
    await write_reg(dut, REG_CONTROL, CTRL_SYSTEM_ENABLE)
    await ClockCycles(dut.clk, 3 * TICK_CYCLES)
    assert (int(dut.uo_out.value) & RAIL_MASK) != RAIL_MASK
    await wait_for_mask(dut, RAIL_MASK, RAIL_MASK, 7 * TICK_CYCLES)


@cocotb.test()
async def test_load_policy_restore_shutdown_force_and_active_reset(dut):
    """Load shedding, tick-staged restoration, reverse shutdown, force, reset."""
    await start_clock(dut)
    await reset_dut(dut)
    await start_running(dut, sequence_delay=0)
    await wait_for_mask(dut, LOAD_MASK, LOAD_MASK, 20)

    await write_repeated_sample(dut, 150)
    await wait_for_mask(dut, LOAD_MASK, 0x30, 30)
    await write_repeated_sample(dut, 80)
    await wait_for_mask(dut, LOAD_MASK, 0x10, 30)
    await write_repeated_sample(dut, 0)
    await wait_for_mask(dut, LOAD_MASK, 0, 30)

    await write_reg(dut, REG_SEQUENCE_DELAY, 1)
    await write_repeated_sample(dut, 200)
    seen_loads = []
    for _ in range(4 * TICK_CYCLES):
        await RisingEdge(dut.clk)
        value = int(dut.uo_out.value) & LOAD_MASK
        if not seen_loads or seen_loads[-1] != value:
            seen_loads.append(value)
        assert_output_invariants(dut)
        if value == LOAD_MASK:
            break
    assert seen_loads[-1] == LOAD_MASK
    assert all(v in (0x00, 0x10, 0x30, 0x70) for v in seen_loads)

    await write_reg(dut, REG_CONTROL, CTRL_SYSTEM_ENABLE | CTRL_FORCE_SHUTDOWN)
    assert (int(dut.uo_out.value) & (RAIL_MASK | LOAD_MASK | FAULT_BIT)) == 0
    await write_reg(dut, REG_SEQUENCE_DELAY, 0)
    await write_reg(dut, REG_CONTROL, CTRL_SYSTEM_ENABLE)
    await wait_for_mask(dut, RAIL_MASK, RAIL_MASK, 2 * TICK_CYCLES)

    await write_reg(dut, REG_SEQUENCE_DELAY, 1)
    await write_reg(dut, REG_CONTROL, 0)
    assert (int(dut.uo_out.value) & LOAD_MASK) == 0
    previous = int(dut.uo_out.value) & RAIL_MASK
    for _ in range(5 * TICK_CYCLES):
        await RisingEdge(dut.clk)
        rails = int(dut.uo_out.value) & RAIL_MASK
        assert rails in (0x0F, 0x07, 0x03, 0x01, 0x00)
        assert rails <= previous
        previous = rails
        assert_output_invariants(dut)
        if rails == 0:
            break
    assert previous == 0

    await write_reg(dut, REG_SEQUENCE_DELAY, 0)
    await write_reg(dut, REG_CONTROL, CTRL_SYSTEM_ENABLE)
    await wait_for_mask(dut, RAIL_MASK, RAIL_MASK, 2 * TICK_CYCLES)
    dut.rst_n.value = 0
    await Timer(20, unit="ns")
    assert int(dut.uo_out.value) == 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
    assert int(dut.uo_out.value) == 0


@cocotb.test()
async def test_each_startup_timeout_and_each_run_pg_loss(dut):
    """All four timeout details and all four PG-loss codes."""
    await start_clock(dut)
    for failing_rail in range(1, 5):
        await reset_dut(dut)
        await configure_quiet_high_power(dut, sequence_delay=0)
        await write_reg(dut, REG_PG_STABLE, 0)
        await write_reg(dut, REG_STARTUP_TIMEOUT, 1)
        await write_reg(dut, REG_MAX_RETRY, 0)
        dut.ui_in.value = 0x0F & ~(1 << (failing_rail - 1))
        # Pre-qualify the rails that are intentionally good.  This keeps the
        # one-tick timeout check independent of the PG synchronizer/filter
        # latency at the instant SYSTEM_ENABLE is asserted.
        await ClockCycles(dut.clk, TICK_CYCLES + 20)
        await write_reg(dut, REG_CONTROL, CTRL_SYSTEM_ENABLE)
        await wait_for_mask(dut, FAULT_BIT, FAULT_BIT, 3 * TICK_CYCLES)
        assert await read_reg(dut, REG_LAST_FAULT) == FAULT_STARTUP_TIMEOUT
        detail = await read_reg(dut, REG_FAULT_DETAIL)
        assert detail == failing_rail, (
            f"startup rail {failing_rail}: expected detail {failing_rail}, got {detail}"
        )
        assert (int(dut.uo_out.value) & (RAIL_MASK | LOAD_MASK)) == 0

    fault_codes = [FAULT_PG1, FAULT_PG2, FAULT_PG3, FAULT_PG4]
    for rail_index, expected_fault in enumerate(fault_codes):
        await reset_dut(dut)
        await start_running(dut, sequence_delay=0)
        await write_reg(dut, REG_MAX_RETRY, 0)
        dut.ui_in.value = 0x0F & ~(1 << rail_index)
        await wait_for_mask(dut, FAULT_BIT, FAULT_BIT, 2 * TICK_CYCLES)
        assert await read_reg(dut, REG_LAST_FAULT) == expected_fault
        assert await read_reg(dut, REG_FAULT_DETAIL) == rail_index + 1
        assert (int(dut.uo_out.value) & (RAIL_MASK | LOAD_MASK)) == 0


@cocotb.test()
async def test_external_fault_priority_latch_and_clear_semantics(dut):
    """Frozen OT-over-OC priority, latch, and physical-source-safe clear."""
    await start_clock(dut)
    await reset_dut(dut)
    dut.ui_in.value = (1 << 4) | (1 << 5)
    await wait_for_mask(dut, FAULT_BIT, FAULT_BIT, 10)
    assert await read_reg(dut, REG_LAST_FAULT) == FAULT_OVERTEMP
    assert await read_reg(dut, REG_FAULT_COUNT) == 1

    await write_reg(dut, REG_CONTROL, CTRL_CLEAR_FAULT)
    assert (int(dut.uo_out.value) & FAULT_BIT) != 0
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 5)
    assert (int(dut.uo_out.value) & FAULT_BIT) != 0
    await write_reg(dut, REG_CONTROL, CTRL_CLEAR_FAULT)
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0
    assert await read_reg(dut, REG_LAST_FAULT) == FAULT_OVERTEMP
    assert await read_reg(dut, REG_FAULT_COUNT) == 1

    await reset_dut(dut)
    dut.ui_in.value = 1 << 4
    await wait_for_mask(dut, FAULT_BIT, FAULT_BIT, 10)
    assert await read_reg(dut, REG_LAST_FAULT) == FAULT_OVERCURRENT
    assert (int(dut.uo_out.value) & (RAIL_MASK | LOAD_MASK)) == 0


@cocotb.test()
async def test_watchdog_run_only_heartbeat_timeout_and_zero_disable(dut):
    """Watchdog resets outside RUN, accepts toggles, and zero disables it."""
    await start_clock(dut)
    await reset_dut(dut)
    await configure_quiet_high_power(dut, sequence_delay=0)
    await write_reg(dut, REG_PG_STABLE, 0)
    await write_reg(dut, REG_STARTUP_TIMEOUT, 0)
    await write_reg(dut, REG_WATCHDOG_TIMEOUT, 2)
    await write_reg(dut, REG_MAX_RETRY, 0)
    await write_reg(
        dut, REG_CONTROL, CTRL_SYSTEM_ENABLE | CTRL_WATCHDOG_ENABLE
    )
    await ClockCycles(dut.clk, 3 * TICK_CYCLES)
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0

    dut.ui_in.value = 0x0F
    await wait_for_mask(dut, RAIL_MASK, RAIL_MASK, 2 * TICK_CYCLES)
    heartbeat = 0
    for _ in range(3):
        await ClockCycles(dut.clk, 600)
        heartbeat ^= 1
        dut.ui_in.value = 0x0F | (heartbeat << 6)
        await ClockCycles(dut.clk, 5)
        assert (int(dut.uo_out.value) & FAULT_BIT) == 0
    await wait_for_mask(dut, FAULT_BIT, FAULT_BIT, 3 * TICK_CYCLES)
    assert await read_reg(dut, REG_LAST_FAULT) == FAULT_WATCHDOG_TIMEOUT

    await reset_dut(dut)
    await start_running(dut, sequence_delay=0)
    await write_reg(dut, REG_WATCHDOG_TIMEOUT, 0)
    await write_reg(
        dut, REG_CONTROL, CTRL_SYSTEM_ENABLE | CTRL_WATCHDOG_ENABLE
    )
    await ClockCycles(dut.clk, 3 * TICK_CYCLES)
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0


@cocotb.test()
async def test_retry_success_exhaustion_root_cause_and_zero_disable(dut):
    """Retry success, exhaustion, root-cause retention, and MAX_RETRY=0."""
    await start_clock(dut)
    await reset_dut(dut)
    await start_running(dut, sequence_delay=0)
    await write_reg(dut, REG_RETRY_DELAY, 0)
    await write_reg(dut, REG_MAX_RETRY, 2)
    dut.ui_in.value = 0x1F
    await wait_for_mask(dut, FAULT_BIT, FAULT_BIT, 10)
    dut.ui_in.value = 0x0F
    await wait_for_mask(dut, RAIL_MASK, RAIL_MASK, 2 * TICK_CYCLES)
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0
    assert await read_reg(dut, REG_RETRY_COUNT) == 1
    assert await read_reg(dut, REG_LAST_FAULT) == FAULT_OVERCURRENT

    await reset_dut(dut)
    await configure_quiet_high_power(dut, sequence_delay=0)
    await write_reg(dut, REG_PG_STABLE, 0)
    await write_reg(dut, REG_STARTUP_TIMEOUT, 1)
    await write_reg(dut, REG_RETRY_DELAY, 0)
    await write_reg(dut, REG_MAX_RETRY, 1)
    dut.ui_in.value = 0
    await write_reg(dut, REG_CONTROL, CTRL_SYSTEM_ENABLE)
    await ClockCycles(dut.clk, 4 * TICK_CYCLES)
    status = await read_reg(dut, REG_STATUS)
    assert (status & 0x10) != 0
    assert await read_reg(dut, REG_LAST_FAULT) == FAULT_STARTUP_TIMEOUT
    assert await read_reg(dut, REG_FAULT_DETAIL) == 1
    assert await read_reg(dut, REG_RETRY_COUNT) == 1
    assert (int(dut.uo_out.value) & (RAIL_MASK | LOAD_MASK)) == 0
    assert (int(dut.uo_out.value) & FAULT_BIT) != 0

    dut.ui_in.value = 0x0F
    await write_reg(
        dut, REG_CONTROL, CTRL_SYSTEM_ENABLE | CTRL_CLEAR_FAULT
    )
    assert (await read_reg(dut, REG_STATUS) & 0x10) == 0
    assert await read_reg(dut, REG_RETRY_COUNT) == 0
    await wait_for_mask(dut, RAIL_MASK, RAIL_MASK, 2 * TICK_CYCLES)

    await write_reg(dut, REG_MAX_RETRY, 0)
    dut.ui_in.value = 0x1F
    await wait_for_mask(dut, FAULT_BIT, FAULT_BIT, 10)
    dut.ui_in.value = 0x0F
    await ClockCycles(dut.clk, 2 * TICK_CYCLES)
    status = await read_reg(dut, REG_STATUS)
    assert (status & 0x10) == 0
    assert await read_reg(dut, REG_RETRY_COUNT) == 0
    assert await read_reg(dut, REG_LAST_FAULT) == FAULT_OVERCURRENT
    assert (int(dut.uo_out.value) & FAULT_BIT) != 0
    await write_reg(
        dut, REG_CONTROL, CTRL_SYSTEM_ENABLE | CTRL_CLEAR_FAULT
    )
    await wait_for_mask(dut, RAIL_MASK, RAIL_MASK, 2 * TICK_CYCLES)
    assert (int(dut.uo_out.value) & FAULT_BIT) == 0


@cocotb.test()
async def test_fault_count_saturation_and_illegal_state_safety(dut):
    """Saturating diagnostics and deterministic illegal rail-state recovery."""
    await start_clock(dut)
    await reset_dut(dut)
    if os.getenv("GATES", "no") != "yes":
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
