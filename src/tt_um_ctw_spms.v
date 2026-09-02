/*
 * CTW-SPMS
 * Programmable Smart Power Management & Supervisor
 *
 * Milestone 1A: SPI ingress + POWER_SAMPLE register
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

    wire       spi_miso;
    wire [6:0] spi_write_addr;
    wire [7:0] spi_write_data;
    wire       power_sample_wr_strobe;

    reg        fault_latched;
    reg  [7:0] power_sample;

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

    spi_slave u_spi_slave (
        .clk             (clk),
        .rst_n           (rst_n),
        .spi_cs_n_async  (uio_in[1]),
        .spi_sclk_async  (uio_in[2]),
        .spi_mosi_async  (uio_in[3]),
        .spi_miso        (spi_miso),
        .read_data_00    (power_sample),
        .write_addr      (spi_write_addr),
        .write_data      (spi_write_data),
        .write_strobe    (power_sample_wr_strobe)
    );

    assign hard_fault_event = overcurrent_sync | overtemp_sync;

    /*
     * Preserve the Milestone 0.1 fail-safe latch. Full fault policy and
     * CLEAR_FAULT behavior arrive in the dedicated fault milestone.
     */
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fault_latched <= 1'b0;
        end else if (hard_fault_event) begin
            fault_latched <= 1'b1;
        end
    end

    /* Minimal Milestone-1A register support: address 0x00 only. */
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            power_sample <= 8'h00;
        end else if (power_sample_wr_strobe && (spi_write_addr == 7'h00)) begin
            power_sample <= spi_write_data;
        end
    end

    /* Rails and loads remain OFF until their later milestones. */
    assign uo_out = {fault_latched, 7'b000_0000};

    /* uio[0] is the only driven bidirectional pin: SPI_MISO. */
    assign uio_out = {7'b000_0000, spi_miso};
    assign uio_oe  = 8'b0000_0001;

    /*
     * These synchronized foundation signals are intentionally retained in
     * source for upcoming milestones but do not affect outputs in 1A.
     */
    wire _unused = &{1'b0,
                     pg1_sync, pg2_sync, pg3_sync, pg4_sync,
                     watchdog_sync, force_shutdown_ext_sync, ena_sync,
                     timer_tick_ce, uio_in[7:4], uio_in[0]};

endmodule

`default_nettype wire
