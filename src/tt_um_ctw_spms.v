/*
 * CTW-SPMS
 * Programmable Smart Power Management & Supervisor
 *
 * Milestone 0.1: real clocked ASIC foundation
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_ctw_spms (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,

    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,

    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);

    wire pg1_sync;
    wire pg2_sync;
    wire pg3_sync;
    wire pg4_sync;
    wire overcurrent_sync;
    wire overtemp_sync;
    wire watchdog_sync;
    wire force_shutdown_ext_sync;
    wire ena_sync;

    wire timer_tick_ce;
    wire hard_fault_event;
    wire pg_all_good;

    reg  fault_latched;
    reg  watchdog_sync_d;
    reg  watchdog_seen;
    reg  foundation_ready;

    sync_2ff u_sync_pg1 (
        .clk      (clk),
        .rst_n    (rst_n),
        .async_in (ui_in[0]),
        .sync_out (pg1_sync)
    );

    sync_2ff u_sync_pg2 (
        .clk      (clk),
        .rst_n    (rst_n),
        .async_in (ui_in[1]),
        .sync_out (pg2_sync)
    );

    sync_2ff u_sync_pg3 (
        .clk      (clk),
        .rst_n    (rst_n),
        .async_in (ui_in[2]),
        .sync_out (pg3_sync)
    );

    sync_2ff u_sync_pg4 (
        .clk      (clk),
        .rst_n    (rst_n),
        .async_in (ui_in[3]),
        .sync_out (pg4_sync)
    );

    sync_2ff u_sync_overcurrent (
        .clk      (clk),
        .rst_n    (rst_n),
        .async_in (ui_in[4]),
        .sync_out (overcurrent_sync)
    );

    sync_2ff u_sync_overtemp (
        .clk      (clk),
        .rst_n    (rst_n),
        .async_in (ui_in[5]),
        .sync_out (overtemp_sync)
    );

    sync_2ff u_sync_watchdog (
        .clk      (clk),
        .rst_n    (rst_n),
        .async_in (ui_in[6]),
        .sync_out (watchdog_sync)
    );

    sync_2ff u_sync_force_shutdown (
        .clk      (clk),
        .rst_n    (rst_n),
        .async_in (ui_in[7]),
        .sync_out (force_shutdown_ext_sync)
    );

    sync_2ff u_sync_ena (
        .clk      (clk),
        .rst_n    (rst_n),
        .async_in (ena),
        .sync_out (ena_sync)
    );

    timebase_tick u_timebase_tick (
        .clk           (clk),
        .rst_n         (rst_n),
        .timer_tick_ce (timer_tick_ce)
    );

    assign hard_fault_event = overcurrent_sync | overtemp_sync;
    assign pg_all_good = pg1_sync & pg2_sync & pg3_sync & pg4_sync;

    /*
     * Hard-fault latch. At Milestone 0.1 only reset can clear it.
     * FORCE_SHUTDOWN_EXT deliberately does not set this latch.
     */
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fault_latched <= 1'b0;
        end else if (hard_fault_event) begin
            fault_latched <= 1'b1;
        end
    end

    /*
     * Retain whether a synchronized watchdog transition has ever been
     * observed since reset. Full watchdog timeout supervision is deferred.
     */
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            watchdog_sync_d <= 1'b0;
            watchdog_seen   <= 1'b0;
        end else begin
            watchdog_sync_d <= watchdog_sync;
            if (watchdog_sync != watchdog_sync_d) begin
                watchdog_seen <= 1'b1;
            end
        end
    end

    /*
     * Future-compatible foundation readiness state. It gives synchronized
     * PG, watchdog, external shutdown, project enable and the 10 kHz
     * clock-enable timebase real functional use without enabling any rail
     * or load. Unsafe state clears readiness immediately on a core clock;
     * qualification into ready occurs only on timer_tick_ce.
     */
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            foundation_ready <= 1'b0;
        end else if (!ena_sync || force_shutdown_ext_sync ||
                     hard_fault_event || fault_latched || !pg_all_good) begin
            foundation_ready <= 1'b0;
        end else if (timer_tick_ce) begin
            foundation_ready <= watchdog_seen;
        end
    end

    /*
     * RAIL1..4 and LOAD1..3 remain OFF for Milestone 0.1.
     * FAULT is the only dedicated output with active functionality.
     */
    assign uo_out = {fault_latched, 7'b000_0000};

    /*
     * uio[0] is reserved for SPI_MISO. SPI is not implemented yet, so all
     * bidirectional pins remain inputs (uio_oe == 0). The internal MISO data
     * path is deterministic and exposes foundation readiness; while not ready,
     * the one-cycle timer tick is visible for foundation verification.
     */
    assign uio_out = {7'b000_0000, (foundation_ready | timer_tick_ce)};
    assign uio_oe  = 8'b0000_0000;

    /* SPI inputs are reserved but intentionally unused in Milestone 0.1. */
    wire _unused = &{uio_in, 1'b0};

endmodule

`default_nettype wire
