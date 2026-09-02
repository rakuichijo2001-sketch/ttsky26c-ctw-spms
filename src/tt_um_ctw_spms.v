/*
 * CTW-SPMS
 * Programmable Smart Power Management & Supervisor
 *
 * Target:
 *   Tiny Tapeout TTSKY26c
 *   SKY130
 *   1x2 tile
 *
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

    /*
     * Baseline safe-state implementation.
     *
     * Functional subsystems will be integrated incrementally:
     *
     *   power_fir
     *       ->
     *   power_deviation
     *       ->
     *   anomaly_detector
     *       ->
     *   power_level_classifier
     *       ->
     *   rail_sequencer
     *       +
     *   load_priority_manager
     *       +
     *   fault_manager
     *       ->
     *   output_safety
     *
     * Until those blocks are integrated, every power-control output
     * remains OFF.
     */

    assign uo_out = 8'b0000_0000;

    /*
     * SPI MISO will eventually use uio[0].
     * During baseline bring-up all bidirectional pins remain inputs.
     */
    assign uio_out = 8'b0000_0000;
    assign uio_oe  = 8'b0000_0000;

    /*
     * Explicitly consume currently-unused inputs.
     * This prevents avoidable lint warnings while preserving the
     * Tiny Tapeout interface.
     */
    wire _unused = &{
        ui_in,
        uio_in,
        ena,
        clk,
        rst_n,
        1'b0
    };

endmodule

`default_nettype wire